/* ============================================================
 * canvas.js — SVG 画布编辑器
 * 负责：元素渲染、多选、分组（gid）、移动/旋转/缩放、框选、
 *       视图平移缩放、坐标换算、出入口磁吸（保持原姿态，仅平移）
 * 撤销快照与属性面板/右键菜单通过回调交给 app.js
 * ============================================================ */
(function () {

  const stage = document.getElementById('stage');
  const wrap = document.getElementById('canvas-wrap');
  const layerEl = document.getElementById('layer-elements');
  const layerOv = document.getElementById('layer-overlay');
  const zoomLabel = document.getElementById('zoom-level');
  const statusPos = document.getElementById('status-pos');
  const statusCount = document.getElementById('status-count');

  const state = {
    elements: [],
    selectedIds: [],       // 支持多选
    view: { scale: 1, tx: 0, ty: 0 },
    snap: true,
    grid: 20,
    showRoad: true,        // 道路图层可见性（工具栏「道路图层」按钮控制）
    drag: null,
    spaceDown: false,
    beforeEdit: null,      // app.js 注入：撤销快照
    onSelectChange: null,  // app.js 注入：属性面板
    onContextMenu: null    // app.js 注入：右键菜单
  };

  /* ---------------- 坐标换算 ---------------- */
  function screenToCanvas(clientX, clientY) {
    const r = stage.getBoundingClientRect();
    const sx = clientX - r.left, sy = clientY - r.top;
    return { x: (sx - state.view.tx) / state.view.scale, y: (sy - state.view.ty) / state.view.scale };
  }

  function genId() {
    return 'el_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }
  function genGid() {
    return 'g_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }

  /* 指针捕获容错：真实指针正常捕获；合成事件/无活跃指针时不致中断后续交互 */
  function safeCapture(pid) {
    try { stage.setPointerCapture(pid); } catch (e) { /* ignore */ }
  }

  /* ---------------- 选择（多选） ---------------- */
  function isSelected(id) { return state.selectedIds.includes(id); }
  function selectedEls() {
    return state.selectedIds
      .map(id => state.elements.find(e => e.id === id))
      .filter(Boolean);
  }
  /* 单选时返回该元素，多选或无选中时返回 null */
  function getSelected() {
    return state.selectedIds.length === 1
      ? (state.elements.find(e => e.id === state.selectedIds[0]) || null)
      : null;
  }
  function setSelection(ids) {
    state.selectedIds = Array.from(new Set(ids))
      .filter(id => state.elements.some(e => e.id === id));
    renderAll();
    if (state.onSelectChange) state.onSelectChange(getSelected(), state.selectedIds);
  }
  function select(id) { setSelection(id == null ? [] : [id]); }

  /* ---------------- 分组（gid） ---------------- */
  function groupMembers(el) {
    if (!el.gid) return [el];
    return state.elements.filter(e => e.gid === el.gid);
  }
  /* 合并两个元素（及其所在组）到同一组 */
  function mergeGroups(elA, elB) {
    const gA = elA.gid, gB = elB.gid;
    if (gA && gB) {
      if (gA === gB) return;
      state.elements.forEach(e => { if (e.gid === gB) e.gid = gA; });
    } else if (gA) { elB.gid = gA; }
    else if (gB) { elA.gid = gB; }
    else { const g = genGid(); elA.gid = g; elB.gid = g; }
  }
  function groupSelected() {
    const els = selectedEls();
    if (els.length < 2) return false;
    const g = genGid();
    els.forEach(e => e.gid = g);
    renderAll();
    return true;
  }
  function ungroupSelected() {
    const gids = new Set(selectedEls().map(e => e.gid).filter(Boolean));
    if (!gids.size) return false;
    state.elements.forEach(e => { if (e.gid && gids.has(e.gid)) e.gid = undefined; });
    renderAll();
    return true;
  }

  /* ---------------- 视图 ---------------- */
  function applyView() {
    const v = state.view;
    document.getElementById('viewport')
      .setAttribute('transform', `matrix(${v.scale},0,0,${v.scale},${r2(v.tx)},${r2(v.ty)})`);
    zoomLabel.textContent = Math.round(v.scale * 100) + '%';
  }

  function zoomAt(screenX, screenY, factor) {
    const r = stage.getBoundingClientRect();
    const mx = screenX - r.left, my = screenY - r.top;
    const v = state.view;
    const ns = Math.min(5, Math.max(0.2, v.scale * factor));
    v.tx = mx - (mx - v.tx) * ns / v.scale;
    v.ty = my - (my - v.ty) * ns / v.scale;
    v.scale = ns;
    applyView();
  }

  function fitView() {
    const cw = wrap.clientWidth, ch = wrap.clientHeight;
    if (!state.elements.length) {
      state.view.scale = 1;
      state.view.tx = cw / 2;
      state.view.ty = ch / 2;
    } else {
      let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
      state.elements.forEach(e => {
        xmin = Math.min(xmin, e.x - e.w / 2); xmax = Math.max(xmax, e.x + e.w / 2);
        ymin = Math.min(ymin, e.y - e.h / 2); ymax = Math.max(ymax, e.y + e.h / 2);
      });
      const pad = 48, bw = xmax - xmin, bh = ymax - ymin;
      const sc = Math.min(4, Math.max(0.12, Math.min((cw - pad * 2) / bw, (ch - pad * 2) / bh)));
      const cx = (xmin + xmax) / 2, cy = (ymin + ymax) / 2;
      state.view.scale = sc;
      state.view.tx = cw / 2 - cx * sc;
      state.view.ty = ch / 2 - cy * sc;
    }
    applyView();
  }

  /* ---------------- 渲染 ---------------- */
  function renderEl(el) {
    const sel = isSelected(el.id) ? ' selected' : '';
    return `<g class="el${sel}" data-id="${el.id}" transform="translate(${r2(el.x)},${r2(el.y)}) rotate(${r2(el.rotation)})">
      <rect class="hit-area" x="${-el.w / 2}" y="${-el.h / 2}" width="${el.w}" height="${el.h}"/>
      ${shapeMarkup(el)}
    </g>`;
  }

  function renderOverlay() {
    const els = selectedEls();
    let m = '';
    els.forEach(el => {
      const hw = el.w / 2, hh = el.h / 2;
      m += `<g transform="translate(${r2(el.x)},${r2(el.y)}) rotate(${r2(el.rotation)})">`;
      m += `<rect class="sel-box" x="${-hw}" y="${-hh}" width="${el.w}" height="${el.h}"/>`;
      if (els.length === 1) {
        [[-hw, -hh], [hw, -hh], [-hw, hh], [hw, hh]].forEach((c, i) => {
          m += `<rect class="sel-handle" data-h="c${i}" x="${c[0] - 3.6}" y="${c[1] - 3.6}" width="7.2" height="7.2" rx="1.4"/>`;
        });
        m += `<line class="sel-handle-line" x1="0" y1="${-hh}" x2="0" y2="${-hh - 17}"/>`;
        m += `<circle class="sel-handle rotate" data-h="rot" cx="0" cy="${-hh - 17}" r="5.2"/>`;
        portsOf(el).forEach(p => {
          const rad = p.normal * Math.PI / 180;
          const ex = 9 * Math.cos(rad), ey = 9 * Math.sin(rad);
          m += `<line x1="${r2(p.x)}" y1="${r2(p.y)}" x2="${r2(p.x + ex)}" y2="${r2(p.y + ey)}" stroke="#28d4ee" stroke-width="1.5"/>`;
          m += `<circle cx="${r2(p.x)}" cy="${r2(p.y)}" r="2.6" fill="#28d4ee"/>`;
        });
      }
      m += '</g>';
    });
    if (state.drag && state.drag.mode === 'marquee' && state.drag.cur) {
      const r = marqueeRect(state.drag);
      m += `<rect class="marquee-rect" x="${r2(r.x0)}" y="${r2(r.y0)}" width="${r2(r.x1 - r.x0)}" height="${r2(r.y1 - r.y0)}"/>`;
    }
    layerOv.innerHTML = m;
  }

  /* 道路图层过滤：隐藏后画布只保留车辆 / 信号灯 / 标志 / 障碍，便于核对任务对象；
   * 被隐藏的道路元素同时失去点击与框选命中（DOM 中已不存在，无需额外判断）。 */
  function visibleEls() {
    return state.showRoad ? state.elements : state.elements.filter(e => e.type !== 'lane');
  }

  function renderAll() {
    layerEl.innerHTML = visibleEls().map(renderEl).join('');
    renderOverlay();
    statusCount.textContent = state.showRoad
      ? '元素 ' + state.elements.length
      : `元素 ${state.elements.length} · 道路已隐藏`;
  }

  /* 道路图层开关：状态与按钮由 app.js 同步；隐藏时清掉看不见的道路选中项 */
  function setRoadVisible(v) {
    state.showRoad = !!v;
    if (!state.showRoad && state.selectedIds.length) {
      const keep = state.selectedIds.filter(id => {
        const el = state.elements.find(e => e.id === id);
        return el && el.type !== 'lane';
      });
      if (keep.length !== state.selectedIds.length) {
        state.selectedIds = keep;
        if (state.onSelectChange) state.onSelectChange(getSelected(), state.selectedIds);
      }
    }
    renderAll();
  }

  /* ---------------- 元素操作 ---------------- */

  /* 图层顺序 = state.elements 数组顺序（SVG 后绘制的在上层）。
   * 道路默认沉底：新拖入 / 复制的 lane 插到第一个非道路元素之前，
   * 车辆、信号灯、标志、障碍因此始终压在路面之上。 */
  function insertByLayer(el) {
    if (el.type !== 'lane') { state.elements.push(el); return; }
    const i = state.elements.findIndex(e => e.type !== 'lane');
    if (i < 0) state.elements.push(el);
    else state.elements.splice(i, 0, el);
  }

  /* 置顶 / 置底：只改变数组位置，其余元素相对顺序保持不变 */
  function reorderSelected(toFront) {
    const ids = new Set(state.selectedIds);
    if (!ids.size) return false;
    const sel = state.elements.filter(e => ids.has(e.id));
    if (!sel.length) return false;
    const rest = state.elements.filter(e => !ids.has(e.id));
    state.elements = toFront ? rest.concat(sel) : sel.concat(rest);
    renderAll();
    return true;
  }

  function bringToFront() { return reorderSelected(true); }
  function sendToBack() { return reorderSelected(false); }

  function addElement(subtype, cx, cy) {
    const cat = CATALOG_MAP[subtype];
    if (!cat) return null;
    const el = {
      id: genId(), type: cat.type, subtype,
      x: Math.round(cx), y: Math.round(cy), rotation: 0,
      w: cat.w, h: cat.h,
      note: '',
      props: JSON.parse(JSON.stringify(cat.props))
    };
    const sz = sizeFromProps(el);
    el.w = sz.w; el.h = sz.h;
    insertByLayer(el);
    select(el.id);
    return el;
  }

  function deleteSelected() {
    const ids = new Set(state.selectedIds);
    if (!ids.size) return;
    state.elements = state.elements.filter(e => !ids.has(e.id));
    setSelection([]);
  }

  function duplicateSelected() {
    const els = selectedEls();
    if (!els.length) return;
    const newGid = els.length > 1 ? genGid() : undefined;
    const copies = els.map(e => {
      const c = JSON.parse(JSON.stringify(e));
      c.id = genId();
      c.x = e.x + state.grid;
      c.y = e.y + state.grid;
      c.gid = newGid;
      insertByLayer(c);
      return c;
    });
    setSelection(copies.map(c => c.id));
  }

  function nudge(dx, dy) {
    const els = selectedEls();
    if (!els.length) return;
    els.forEach(e => { e.x += dx; e.y += dy; });
    renderAll();
    if (state.onSelectChange) state.onSelectChange(getSelected(), state.selectedIds);
  }

  /* 刷新单个元素（属性面板修改后） */
  function refresh(el, keepSize) {
    if (!keepSize) {
      const sz = sizeFromProps(el);
      el.w = sz.w; el.h = sz.h;
    }
    renderAll();
  }

  /* ---------------- 出入口（Port）衔接 ---------------- */
  function portsOf(el) {
    return (PORTS[el.subtype] ? PORTS[el.subtype](el) : []);
  }

  /* 局部端口 → 世界坐标（含旋转后的法线角度） */
  function worldPort(el, port) {
    const rad = el.rotation * Math.PI / 180;
    const cos = Math.cos(rad), sin = Math.sin(rad);
    return {
      x: el.x + port.x * cos - port.y * sin,
      y: el.y + port.x * sin + port.y * cos,
      normal: port.normal + el.rotation,
      width: port.width
    };
  }

  /* 移动时寻找最近出入口对：保持原姿态（不旋转），仅平移使端口重合；返回吸附信息 */
  function applyPortSnap(el) {
    const myPorts = portsOf(el);
    if (!myPorts.length) return null;
    let best = null;
    state.elements.forEach(other => {
      if (other.id === el.id) return;
      if (el.gid && other.gid === el.gid) return;   // 不吸附同组元素
      portsOf(other).forEach(op => {
        const ow = worldPort(other, op);
        myPorts.forEach(mp => {
          const mw = worldPort(el, mp);
          const dist = Math.hypot(mw.x - ow.x, mw.y - ow.y);
          if (dist < 18 && (!best || dist < best.dist)) best = { dist, mp, ow, other };
        });
      });
    });
    if (!best) return null;
    const { mp, ow } = best;
    const nw = worldPort(el, mp);
    el.x += ow.x - nw.x;
    el.y += ow.y - nw.y;
    return best;
  }

  /* ---------------- 指针交互 ---------------- */
  stage.addEventListener('pointerdown', e => {
    if (e.button === 2) return;                       // 右键交给 contextmenu
    if (e.button === 1) { e.preventDefault(); startPan(e); return; }  // 中键平移
    const handle = e.target.closest('.sel-handle');
    const elG = e.target.closest('.el');
    if (handle) { startHandle(e, handle); return; }
    if (elG) {
      if (e.shiftKey) {                              // Shift+点击 切换多选
        const sid = elG.dataset.id;
        setSelection(isSelected(sid)
          ? state.selectedIds.filter(x => x !== sid)
          : state.selectedIds.concat(sid));
      }
      startMove(e, elG);
      return;
    }
    if (state.spaceDown || e.altKey) startPan(e);    // 空格/Alt + 左键 平移
    else startMarquee(e);                            // 空白左键：框选
  });

  function startMove(e, elG) {
    const id = elG.dataset.id;
    if (!isSelected(id)) setSelection([id]);
    const lead = state.elements.find(x => x.id === id);
    let members;
    if (isSelected(id)) members = selectedEls();
    else members = groupMembers(lead);
    state.beforeEdit && state.beforeEdit();
    safeCapture(e.pointerId);
    state.drag = {
      mode: 'move',
      leadId: id,
      members: members.map(x => x.id),
      orig: members.map(x => ({ x: x.x, y: x.y })),
      client0: { x: e.clientX, y: e.clientY },
      moved: false,
      pendingSnap: null
    };
  }

  function startHandle(e, handle) {
    const el = getSelected();
    if (!el) return;
    state.beforeEdit && state.beforeEdit();
    safeCapture(e.pointerId);
    state.drag = {
      mode: handle.dataset.h === 'rot' ? 'rotate' : 'resize',
      corner: handle.dataset.h,
      p0: screenToCanvas(e.clientX, e.clientY),
      o: { w: el.w, h: el.h, rotation: el.rotation }
    };
  }

  function startPan(e) {
    safeCapture(e.pointerId);
    stage.classList.add('panning');
    state.drag = {
      mode: 'pan',
      p0: { x: e.clientX, y: e.clientY },
      o: { tx: state.view.tx, ty: state.view.ty }, moved: false
    };
  }

  function startMarquee(e) {
    safeCapture(e.pointerId);
    const p0 = screenToCanvas(e.clientX, e.clientY);
    state.drag = {
      mode: 'marquee',
      p0, cur: p0,
      client0: { x: e.clientX, y: e.clientY },
      moved: false
    };
  }

  /* 统一的网格吸附位移，保持组内相对位置不变 */
  function moveDelta(origV, deltaV) {
    if (state.snap) return Math.round((origV + deltaV) / state.grid) * state.grid - origV;
    return Math.round(origV + deltaV) - origV;
  }

  function marqueeRect(d) {
    return {
      x0: Math.min(d.p0.x, d.cur.x), x1: Math.max(d.p0.x, d.cur.x),
      y0: Math.min(d.p0.y, d.cur.y), y1: Math.max(d.p0.y, d.cur.y)
    };
  }
  function hitByMarquee(r) {
    return visibleEls().filter(e => {
      const xmin = e.x - e.w / 2, xmax = e.x + e.w / 2;
      const ymin = e.y - e.h / 2, ymax = e.y + e.h / 2;
      return xmax >= r.x0 && xmin <= r.x1 && ymax >= r.y0 && ymin <= r.y1;
    }).map(e => e.id);
  }

  stage.addEventListener('pointermove', e => {
    const p = screenToCanvas(e.clientX, e.clientY);
    statusPos.textContent = `X ${Math.round(p.x)} · Y ${Math.round(p.y)}`;
    const d = state.drag;
    if (!d) return;

    if (d.mode === 'move') {
      if (Math.abs(e.clientX - d.client0.x) + Math.abs(e.clientY - d.client0.y) > 2) d.moved = true;
      const ddx = (e.clientX - d.client0.x) / state.view.scale;
      const ddy = (e.clientY - d.client0.y) / state.view.scale;
      const memberEls = d.members.map(id => state.elements.find(x => x.id === id)).filter(Boolean);
      const lead = state.elements.find(x => x.id === d.leadId);
      const leadIdx = d.members.indexOf(d.leadId);
      const mvx = moveDelta(d.orig[leadIdx].x, ddx);
      const mvy = moveDelta(d.orig[leadIdx].y, ddy);
      memberEls.forEach((mel, i) => { mel.x = d.orig[i].x + mvx; mel.y = d.orig[i].y + mvy; });
      d.pendingSnap = null;
      if (!e.ctrlKey) {
        const before = { x: lead.x, y: lead.y };
        const snapInfo = applyPortSnap(lead);
        if (snapInfo) {
          const sx = lead.x - before.x, sy = lead.y - before.y;
          memberEls.forEach(mel => { if (mel.id !== lead.id) { mel.x += sx; mel.y += sy; } });
          d.pendingSnap = snapInfo;
        }
      }
      renderAll();
    } else if (d.mode === 'rotate') {
      const el = getSelected();
      let ang = Math.atan2(p.y - el.y, p.x - el.x) * 180 / Math.PI + 90;
      el.rotation = e.shiftKey ? Math.round(ang / 15) * 15 : Math.round(ang * 10) / 10;
      renderAll();
    } else if (d.mode === 'resize') {
      const el = getSelected();
      const dx = p.x - el.x, dy = p.y - el.y;
      const rad = -el.rotation * Math.PI / 180;
      const lx = dx * Math.cos(rad) - dy * Math.sin(rad);
      const ly = dx * Math.sin(rad) + dy * cos(rad);
      el.w = Math.min(2400, Math.max(16, Math.round(2 * Math.abs(lx))));
      el.h = Math.min(2400, Math.max(16, Math.round(2 * Math.abs(ly))));
      renderAll();
    } else if (d.mode === 'pan') {
      if (Math.abs(e.clientX - d.p0.x) + Math.abs(e.clientY - d.p0.y) > 3) d.moved = true;
      state.view.tx = d.o.tx + (e.clientX - d.p0.x);
      state.view.ty = d.o.ty + (e.clientY - d.p0.y);
      applyView();
    } else if (d.mode === 'marquee') {
      if (Math.abs(e.clientX - d.client0.x) + Math.abs(e.clientY - d.client0.y) > 3) d.moved = true;
      d.cur = screenToCanvas(e.clientX, e.clientY);
      renderOverlay();
    }
  });

  stage.addEventListener('pointerup', () => {
    const d = state.drag;
    if (!d) return;
    if (d.mode === 'pan') {
      stage.classList.remove('panning');
    } else if (d.mode === 'marquee') {
      if (d.moved) setSelection(hitByMarquee(marqueeRect(d)));
      else setSelection([]);                       // 空白点击 = 取消选中
    } else if (d.mode === 'move') {
      if (d.pendingSnap) {                         // 吸附成功 → 自动组合
        const lead = state.elements.find(x => x.id === d.leadId);
        const other = state.elements.find(x => x.id === d.pendingSnap.other.id);
        if (lead && other) mergeGroups(lead, other);
      }
    }
    state.drag = null;
  });

  /* 右键：定位元素并交由 app.js 弹出菜单 */
  stage.addEventListener('contextmenu', e => {
    e.preventDefault();
    const elG = e.target.closest('.el');
    if (elG) {
      const id = elG.dataset.id;
      if (!isSelected(id)) setSelection([id]);
    }
    if (state.onContextMenu) state.onContextMenu(e.clientX, e.clientY, selectedEls());
  });

  /* 空格临时抓手 */
  function isFormTarget(t) {
    return ['input', 'textarea', 'select'].includes((t.tagName || '').toLowerCase());
  }
  document.addEventListener('keydown', e => {
    if (e.code === 'Space' && !isFormTarget(e.target)) {
      state.spaceDown = true;
      stage.classList.add('panning');
    }
  });
  document.addEventListener('keyup', e => {
    if (e.code === 'Space') {
      state.spaceDown = false;
      stage.classList.remove('panning');
    }
  });

  /* 滚轮缩放（以鼠标为锚点） */
  wrap.addEventListener('wheel', e => {
    e.preventDefault();
    zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? 1.12 : 1 / 1.12);
  }, { passive: false });

  /* ---------------- 序列化 ---------------- */
  function serialize(name) {
    return {
      version: '1.1',
      meta: {
        name: name || document.getElementById('track-name').value || '未命名赛道',
        grid: state.grid,
        pixels_per_meter: PPM,
        saved_at: new Date().toLocaleString('zh-CN', { hour12: false })
      },
      view: state.view,
      elements: state.elements
    };
  }

  function deserialize(data) {
    if (!data || !Array.isArray(data.elements)) throw new Error('JSON 缺少 elements 数组');
    state.elements = data.elements.map(e => ensureCarProps(Object.assign({
      id: genId(), type: 'lane', subtype: 'straight', rotation: 0, props: {}, gid: undefined, note: ''
    }, e)));
    if (data.view) state.view = Object.assign({ scale: 1, tx: 0, ty: 0 }, data.view);
    state.selectedIds = [];
    applyView();
    renderAll();
    if (state.onSelectChange) state.onSelectChange(null, []);
  }

  function clearAll() {
    state.elements = [];
    setSelection([]);
  }

  /* 将视图居中到指定元素并高亮选中（供“场景中元素统计”面板定位用） */
  function focusElement(id) {
    const el = state.elements.find(e => e.id === id);
    if (!el) return false;
    const v = state.view;
    v.tx = wrap.clientWidth / 2 - el.x * v.scale;
    v.ty = wrap.clientHeight / 2 - el.y * v.scale;
    applyView();
    setSelection([id]);
    return true;
  }

  function r2(v) { return Math.round(v * 100) / 100; }

  /* ---------------- 对外接口 ---------------- */
  window.Editor = {
    state,
    addElement, deleteSelected, duplicateSelected,
    bringToFront, sendToBack,
    select, setSelection, nudge, refresh, renderAll,
    setRoadVisible, visibleEls,
    screenToCanvas, fitView, zoomAt, focusElement,
    serialize, deserialize, clearAll, getSelected, selectedEls,
    portsOf, worldPort, applyPortSnap,
    groupSelected, ungroupSelected, mergeGroups
  };

  fitView();
  renderAll();
})();
