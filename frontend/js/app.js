/* ============================================================
 * app.js — 主控：元素库、DnD、属性面板、撤销重做、API、快捷键
 * ============================================================ */

const $ = s => document.querySelector(s);
const paletteGroups = $('#palette-groups');
const inspectorBody = $('#inspector-body');
const tip = $('#canvas-tip');
const statsBody = $('#stats-body');

/* HTML 转义，防止备注等用户输入破坏面板结构 */
function escHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* ============================================================
 * 一、撤销 / 重做
 * ============================================================ */
let undoStack = [], redoStack = [];
const MAX_UNDO = 50;

function snapshot() { return JSON.stringify(Editor.serialize()); }
function pushUndo() {
  undoStack.push(snapshot());
  if (undoStack.length > MAX_UNDO) undoStack.shift();
  redoStack = [];
  updateUndoBtns();
}
function undo() {
  if (!undoStack.length) return;
  redoStack.push(snapshot());
  Editor.deserialize(JSON.parse(undoStack.pop()));
  updateUndoBtns();
  updateTip();
}
function redo() {
  if (!redoStack.length) return;
  undoStack.push(snapshot());
  Editor.deserialize(JSON.parse(redoStack.pop()));
  updateUndoBtns();
  updateTip();
}
function updateUndoBtns() {
  $('#btn-undo').disabled = !undoStack.length;
  $('#btn-redo').disabled = !redoStack.length;
}
Editor.state.beforeEdit = pushUndo;
Editor.state.onSelectChange = (el, ids) => { renderInspector(el, ids); updateTip(); };

/* ============================================================
 * 二、左侧元素库渲染
 * ============================================================ */
PALETTE.forEach(group => {
  const g = document.createElement('div');
  g.className = 'palette-group';
  const head = document.createElement('div');
  head.className = 'group-head';
  head.innerHTML = `<span>${group.label}</span><span class="arrow">▼</span>`;
  head.addEventListener('click', () => g.classList.toggle('collapsed'));

  const items = document.createElement('div');
  items.className = 'group-items';
  group.items.forEach(it => {
    const cell = document.createElement('div');
    cell.className = 'palette-item';
    cell.draggable = true;
    cell.dataset.subtype = it.subtype;
    cell.innerHTML = `<span class="pv">${previewThumb(it.subtype)}</span><span class="pl">${it.label}</span>`;
    cell.addEventListener('dragstart', e => {
      e.dataTransfer.setData('text/subtype', it.subtype);
      e.dataTransfer.effectAllowed = 'copy';
    });
    items.appendChild(cell);
  });

  g.appendChild(head);
  g.appendChild(items);
  paletteGroups.appendChild(g);
});

/* 左侧面板 Tab 切换：元素库 / 场景中元素统计 */
document.querySelectorAll('.panel-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const toStats = tab.dataset.tab === 'stats';
    document.querySelectorAll('.panel-tab').forEach(t => t.classList.toggle('active', t === tab));
    paletteGroups.hidden = toStats;
    statsBody.hidden = !toStats;
    if (toStats) renderSceneStats();
  });
});

/* ============================================================
 * 三、拖拽放置到画布
 * ============================================================ */
const stage = $('#stage');
stage.addEventListener('dragover', e => {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'copy';
  stage.classList.add('dragging-over');
});
stage.addEventListener('dragleave', e => {
  if (e.target === stage) stage.classList.remove('dragging-over');
});
stage.addEventListener('drop', e => {
  e.preventDefault();
  stage.classList.remove('dragging-over');
  const subtype = e.dataTransfer.getData('text/subtype');
  if (!subtype) return;
  const p = Editor.screenToCanvas(e.clientX, e.clientY);
  pushUndo();
  Editor.addElement(subtype, p.x, p.y);
  updateTip();
});

/* ============================================================
 * 四、属性面板
 * ============================================================ */
function renderInspector(el, ids) {
  if (!el) {
    if (ids && ids.length > 1) {
      inspectorBody.innerHTML = `<div class="inspector-empty">
        <svg viewBox="0 0 24 24" width="40" height="40"><path d="M4 7h16M4 12h16M4 17h16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        <p>已选中 ${ids.length} 个元素</p>
        <div class="insp-multi-actions">
          <button class="btn" id="multi-group">组合为模块</button>
          <button class="btn" id="multi-ungroup">取消组合</button>
        </div>
      </div>`;
      const gBtn = $('#multi-group'), uBtn = $('#multi-ungroup');
      if (gBtn) gBtn.addEventListener('click', () => { pushUndo(); Editor.groupSelected(); });
      if (uBtn) uBtn.addEventListener('click', () => { pushUndo(); Editor.ungroupSelected(); });
      return;
    }
    inspectorBody.innerHTML = `<div class="inspector-empty">
      <svg viewBox="0 0 24 24" width="40" height="40"><path d="M12 2l2.4 6.9H22l-6 4.4 2.3 7.2L12 16.2 5.7 20.5 8 13.3 2 8.9h7.6z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>
      <p>选中画布中的元素<br>在此编辑其参数</p></div>`;
    return;
  }

  let html = `<div class="insp-id">ID: ${el.id}</div>`;

  /* 位置与旋转 */
  html += `<div class="insp-section"><h4>位置与旋转</h4>
    <div class="insp-row">
      ${numFieldHTML('__x', 'X 坐标', el.x, 0)}
      ${numFieldHTML('__y', 'Y 坐标', el.y, 0)}
    </div>
    <div class="insp-field">${numFieldHTML('__r', '旋转角度', el.rotation, 0, '°')}</div>
  </div>`;

  schemaOf(el.subtype, el.type).forEach(sec => {
    html += `<div class="insp-section"><h4>${sec.section}</h4>`;
    sec.fields.forEach(f => { html += fieldHTML(f, el.props[f.key]); });
    html += `</div>`;
  });

  /* 备注：说明该模块 id 对应的功能，默认空 */
  html += `<div class="insp-section"><h4>备注</h4>
    <div class="insp-field">
      <textarea class="form-input" id="insp-note" rows="3" placeholder="说明该模块（${escHtml(el.id)}）的功能…">${escHtml(el.note || '')}</textarea>
    </div>
    <p class="form-hint">模块 ID：${escHtml(el.id)}</p>
  </div>`;

  html += `<div class="insp-danger-zone">
    <button class="btn" id="insp-dup">复制元素</button>
    <button class="btn btn-danger-ghost" id="insp-del">删除元素</button>
  </div>`;
  inspectorBody.innerHTML = html;

  bindInspector(el);
};

function fieldHTML(f, val) {
  if (f.type === 'check') {
    return `<div class="insp-field"><label class="insp-check"><input type="checkbox" data-k="${f.key}" ${val ? 'checked' : ''}> ${f.label}</label></div>`;
  }
  if (f.type === 'select') {
    const opts = f.options.map(o => `<option value="${o[0]}" ${String(o[0]) === String(val) ? 'selected' : ''}>${o[1]}</option>`).join('');
    return `<div class="insp-field"><label>${f.label}</label><select class="form-select" data-k="${f.key}">${opts}</select></div>`;
  }
  if (f.type === 'color') {
    return `<div class="insp-field"><label>${f.label}</label><input type="color" class="form-input" style="height:34px;padding:3px" data-k="${f.key}" value="${val}"></div>`;
  }
  if (f.type === 'text') {
    return `<div class="insp-field"><label>${f.label}</label><input type="text" class="form-input" data-k="${f.key}" value="${val == null ? '' : val}"></div>`;
  }
  return numFieldHTML(f.key, f.label, val, f.step, f.unit, f.min, f.max);
}

function numFieldHTML(key, label, val, step, unit, min, max) {
  return `<div class="insp-field"><label>${label}${unit ? ` <span class="unit">(${unit})</span>` : ''}</label>
    <input type="number" class="form-input" data-k="${key}" value="${val}"
    ${step != null ? `step="${step}"` : ''} ${min != null ? `min="${min}"` : ''} ${max != null ? `max="${max}"` : ''}></div>`;
}

function bindInspector(el) {
  $('#insp-del').addEventListener('click', () => { pushUndo(); Editor.deleteSelected(); updateTip(); });
  $('#insp-dup').addEventListener('click', () => { pushUndo(); Editor.duplicateSelected(); updateTip(); });

  /* 备注输入：随元素存储，并同步刷新统计面板中的说明 */
  const noteEl = $('#insp-note');
  if (noteEl) {
    noteEl.addEventListener('focus', () => pushUndo());
    noteEl.addEventListener('input', () => { el.note = noteEl.value; renderSceneStats(); });
  }

  inspectorBody.querySelectorAll('input,select').forEach(inp => {
    const key = inp.dataset.k;
    const isBase = key.startsWith('__');
    const field = !isBase ? schemaOf(el.subtype, el.type)
      .flatMap(s => s.fields).find(f => f.key === key) : null;

    inp.addEventListener('focus', () => { if (inp.type === 'number') pushUndo(); });
    inp.addEventListener('change', () => { if (inp.type !== 'number') pushUndo(); applyVal(); });
    inp.addEventListener('input', () => { if (inp.type === 'number') applyVal(true); });

    function applyVal(live) {
      let v;
      if (inp.type === 'checkbox') v = inp.checked;
      else if (inp.type === 'number') {
        v = parseFloat(inp.value);
        if (Number.isNaN(v)) return;
        if (field && field.min != null) v = Math.max(field.min, v);
        if (field && field.max != null) v = Math.min(field.max, v);
      } else {
        v = inp.value;
        // 数字型下拉（车道宽/曲率/弧度/车道数等）转 Number，字符串型（方向/模式等）保持
        if (field && field.options.length && !Number.isNaN(Number(field.options[0][0]))) v = Number(v);
      }

      if (isBase) {
        if (key === '__x') el.x = v;
        if (key === '__y') el.y = v;
        if (key === '__r') el.rotation = v;
        Editor.renderAll();
      } else {
        el.props[key] = v;
        Editor.refresh(el, !field.resize);
      }
      if (!live) renderInspector(el);
    }
  });
}

/* ============================================================
 * 五、工具栏：保存 / 加载 / 导入 / 导出 / 清空
 * ============================================================ */
function toast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  $('#toast-wrap').appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(() => t.remove(), 320); }, 2600);
}

/* 保存 */
$('#btn-save').addEventListener('click', () => {
  $('#save-name').value = $('#track-name').value;
  showModal('modal-save');
  setTimeout(() => $('#save-name').focus(), 50);
});
$('#confirm-save').addEventListener('click', async () => {
  const name = $('#save-name').value.trim();
  if (!name) return toast('请填写赛道名称', 'error');
  try {
    const resp = await fetch(`/api/tracks/${encodeURIComponent(name)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Editor.serialize(name))
    });
    const result = await resp.json();
    if (!resp.ok) throw new Error(result.description || '保存失败');
    $('#track-name').value = name;
    hideModal('modal-save');
    toast('赛道已保存到 ' + (result.path || 'tracks/'), 'success');
  } catch (err) {
    toast('保存失败：' + err.message + '（可改用导出JSON）', 'error');
  }
});

/* 加载列表 */
$('#btn-load').addEventListener('click', openLoadModal);
async function openLoadModal() {
  showModal('modal-load');
  const list = $('#load-list');
  list.innerHTML = '<div class="load-empty">加载中…</div>';
  try {
    const resp = await fetch('/api/tracks');
    if (!resp.ok) throw new Error('列表获取失败');
    const data = await resp.json();
    if (!data.tracks.length) {
      list.innerHTML = '<div class="load-empty">服务器上还没有保存的赛道<br>请先点击“保存”或使用“导入JSON”</div>';
      return;
    }
    list.innerHTML = '';
    data.tracks.forEach(t => {
      const item = document.createElement('div');
      item.className = 'load-item';
      item.innerHTML = `<div class="li-main">
        <div class="li-name">${t.name}</div>
        <div class="li-meta">${t.updated_at || ''} · 元素 ${t.element_count} · ${(t.size / 1024).toFixed(1)} KB</div>
      </div><button class="li-del" title="删除">×</button>`;
      item.addEventListener('click', async () => {
        const r = await fetch(`/api/tracks/${encodeURIComponent(t.name)}`);
        Editor.deserialize(await r.json());
        $('#track-name').value = t.name;
        hideModal('modal-load');
        updateTip();
        toast('已加载赛道：' + t.name, 'success');
      });
      item.querySelector('.li-del').addEventListener('click', async e => {
        e.stopPropagation();
        if (!confirm(`确认删除赛道「${t.name}」？`)) return;
        await fetch(`/api/tracks/${encodeURIComponent(t.name)}`, { method: 'DELETE' });
        openLoadModal();
      });
      list.appendChild(item);
    });
  } catch (err) {
    list.innerHTML = '<div class="load-empty">无法连接后端服务<br>请确认 Python 服务已启动，或使用“导入JSON”</div>';
  }
}

/* 导出到本地文件 */
$('#btn-export').addEventListener('click', () => {
  const name = $('#track-name').value || '未命名赛道';
  const blob = new Blob([JSON.stringify(Editor.serialize(name), null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name + '.json';
  a.click();
  URL.revokeObjectURL(a.href);
  toast('JSON 文件已导出', 'success');
});

/* 从 tracks/ 目录导入（默认），后端列目录；同时保留本地文件选择作为兜底 */
$('#btn-import').addEventListener('click', openImportModal);
async function openImportModal() {
  showModal('modal-import');
  const list = $('#import-list');
  list.innerHTML = '<div class="load-empty">读取 tracks/ 目录…</div>';
  try {
    const resp = await fetch('/api/tracks');
    if (!resp.ok) throw new Error('目录读取失败');
    const data = await resp.json();
    if (!data.tracks.length) {
      list.innerHTML = '<div class="load-empty">tracks/ 目录下暂无 JSON 文件<br>请点击“从本地文件选择…”导入，或先保存赛道</div>';
      return;
    }
    list.innerHTML = '';
    data.tracks.forEach(t => {
      const item = document.createElement('div');
      item.className = 'load-item';
      item.innerHTML = `<div class="li-main">
        <div class="li-name">${t.name}.json</div>
        <div class="li-meta">${t.updated_at || ''} · 元素 ${t.element_count} · ${(t.size / 1024).toFixed(1)} KB</div>
      </div>`;
      item.addEventListener('click', async () => {
        const r = await fetch(`/api/tracks/${encodeURIComponent(t.name)}`);
        if (!r.ok) return toast('导入失败：文件读取失败', 'error');
        pushUndo();
        try {
          Editor.deserialize(await r.json());
          hideModal('modal-import');
          updateTip();
          toast('已从 tracks/ 导入：' + t.name + '.json', 'success');
        } catch (err) {
          undoStack.pop();
          toast('导入失败：' + err.message, 'error');
        }
      });
      list.appendChild(item);
    });
  } catch (err) {
    list.innerHTML = '<div class="load-empty">无法连接后端服务，无法读取 tracks/ 目录<br>请点击“从本地文件选择…”导入</div>';
  }
}

$('#btn-import-local').addEventListener('click', () => $('#file-import').click());
$('#file-import').addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      pushUndo();
      Editor.deserialize(JSON.parse(reader.result));
      updateTip();
      toast('赛道 JSON 已导入', 'success');
    } catch (err) {
      undoStack.pop();
      toast('导入失败：' + err.message, 'error');
    }
  };
  reader.readAsText(file);
  e.target.value = '';
});

/* 清空 */
$('#btn-clear').addEventListener('click', () => {
  if (!Editor.state.elements.length) return;
  if (!confirm('确认清空画布上的全部元素？此操作可撤销。')) return;
  pushUndo();
  Editor.clearAll();
  updateTip();
});

/* 撤销重做按钮 */
$('#btn-undo').addEventListener('click', undo);
$('#btn-redo').addEventListener('click', redo);

/* 缩放按钮 */
$('#zoom-in').addEventListener('click', () => Editor.zoomAt(
  $('#canvas-wrap').getBoundingClientRect().left + $('#canvas-wrap').clientWidth / 2,
  $('#canvas-wrap').getBoundingClientRect().top + $('#canvas-wrap').clientHeight / 2, 1.2));
$('#zoom-out').addEventListener('click', () => Editor.zoomAt(
  $('#canvas-wrap').getBoundingClientRect().left + $('#canvas-wrap').clientWidth / 2,
  $('#canvas-wrap').getBoundingClientRect().top + $('#canvas-wrap').clientHeight / 2, 1 / 1.2));
$('#zoom-fit').addEventListener('click', Editor.fitView);

/* 吸附开关 */
$('#snap-check').addEventListener('change', e => { Editor.state.snap = e.target.checked; });

/* 道路图层开关：隐藏后只保留车辆 / 信号灯 / 标志 / 障碍，便于核对任务对象位置 */
function setRoadLayer(visible) {
  Editor.setRoadVisible(visible);
  const btn = $('#btn-road-layer');
  if (btn) {
    btn.classList.toggle('active', visible);
    btn.setAttribute('aria-pressed', String(visible));
  }
}
function toggleRoadLayer() {
  const next = !Editor.state.showRoad;
  setRoadLayer(next);
  toast(next ? '道路图层：显示' : '道路图层：隐藏（仅显示车辆 / 信号 / 标志 / 障碍）', 'success');
}
$('#btn-road-layer').addEventListener('click', toggleRoadLayer);

/* ============================================================
 * 六、键盘快捷键
 * ============================================================ */
document.addEventListener('keydown', e => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (['input', 'textarea', 'select'].includes(tag)) return;

  const ctrl = e.ctrlKey || e.metaKey;
  if (ctrl && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
  if (ctrl && e.key.toLowerCase() === 'y') { e.preventDefault(); redo(); return; }
  if (ctrl && e.key.toLowerCase() === 'd') { e.preventDefault(); pushUndo(); Editor.duplicateSelected(); return; }
  if (ctrl && e.key === ']') { e.preventDefault(); pushUndo(); Editor.bringToFront(); updateTip(); return; }
  if (ctrl && e.key === '[') { e.preventDefault(); pushUndo(); Editor.sendToBack(); updateTip(); return; }

  if (!ctrl && e.key.toLowerCase() === 'r') { e.preventDefault(); toggleRoadLayer(); return; }

  if (e.key === 'Delete' || e.key === 'Backspace') { pushUndo(); Editor.deleteSelected(); updateTip(); return; }
  if (e.key === 'Escape') { Editor.select(null); return; }

  const step = e.shiftKey ? 10 : 1;
  const map = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
  if (map[e.key]) { e.preventDefault(); pushUndo(); Editor.nudge(map[e.key][0], map[e.key][1]); }
});

/* ============================================================
 * 七、弹窗与提示
 * ============================================================ */
function showModal(id) { $('#' + id).hidden = false; }
function hideModal(id) { $('#' + id).hidden = true; }
document.querySelectorAll('[data-close]').forEach(b =>
  b.addEventListener('click', () => hideModal(b.dataset.close)));
document.querySelectorAll('.modal-mask').forEach(m =>
  m.addEventListener('mousedown', e => { if (e.target === m) m.hidden = true; }));

/* ============================================================
 * 场景中元素统计：按类别折叠，点击元素定位并高亮选中
 * ============================================================ */
const statsCollapsed = {};

function renderSceneStats() {
  if (!statsBody) return;
  const els = Editor.state.elements;
  const known = new Set(PALETTE.map(g => g.group));
  const groups = PALETTE.map(g => ({
    key: g.group,
    label: g.label.replace(/\s+[A-Za-z].*$/, ''),
    items: els.filter(e => e.type === g.group)
  }));
  const others = els.filter(e => !known.has(e.type));
  if (others.length) groups.push({ key: '_other', label: '其他', items: others });

  groups.forEach(g => { if (!(g.key in statsCollapsed)) statsCollapsed[g.key] = true; });
  const active = new Set(Editor.state.selectedIds);

  statsBody.innerHTML = groups.map(g => {
    const collapsed = statsCollapsed[g.key];
    let rows = '';
    if (!collapsed) {
      rows = g.items.length
        ? g.items.map(e => {
          const label = CATALOG_MAP[e.subtype] ? CATALOG_MAP[e.subtype].label : e.subtype;
          const title = `ID: ${e.id}\n备注: ${e.note || '（空）'}\n坐标: (${Math.round(e.x)}, ${Math.round(e.y)})`;
          return `<div class="stats-item${active.has(e.id) ? ' active' : ''}" data-id="${escHtml(e.id)}" title="${escHtml(title)}">
            <span class="si-dot"></span><span class="si-label">${escHtml(label)}</span><span class="si-id">${escHtml(e.id)}</span>
          </div>`;
        }).join('')
        : '<div class="stats-empty">暂无元素</div>';
    }
    return `<div class="stats-group">
      <div class="stats-group-head" data-key="${escHtml(g.key)}">
        <span class="sg-arrow">${collapsed ? '▸' : '▾'}</span>
        <span class="sg-name">${escHtml(g.label)}</span>
        <span class="sg-count">${g.items.length}</span>
      </div>${rows ? `<div class="stats-list">${rows}</div>` : ''}
    </div>`;
  }).join('');

  statsBody.querySelectorAll('.stats-group-head').forEach(h => {
    h.addEventListener('click', () => {
      statsCollapsed[h.dataset.key] = !statsCollapsed[h.dataset.key];
      renderSceneStats();
    });
  });
  statsBody.querySelectorAll('.stats-item').forEach(row => {
    row.addEventListener('click', () => Editor.focusElement(row.dataset.id));
  });
}

function updateTip() {
  tip.classList.toggle('hidden', Editor.state.elements.length > 0);
  renderSceneStats();
}

updateUndoBtns();
updateTip();

/* ============================================================
 * 八、右键上下文菜单
 * ============================================================ */
const ctxMenu = document.createElement('div');
ctxMenu.className = 'context-menu';
ctxMenu.hidden = true;
document.body.appendChild(ctxMenu);

function hideCtx() { ctxMenu.hidden = true; }

function showCtx(cx, cy, items) {
  ctxMenu.innerHTML = items.map((it, i) =>
    `<button class="cm-item${it.danger ? ' danger' : ''}" data-i="${i}">${it.label}</button>`).join('');
  ctxMenu.hidden = false;
  const r = ctxMenu.getBoundingClientRect();
  const left = Math.min(cx, window.innerWidth - r.width - 8);
  const top = Math.min(cy, window.innerHeight - r.height - 8);
  ctxMenu.style.left = Math.max(8, left) + 'px';
  ctxMenu.style.top = Math.max(8, top) + 'px';
  ctxMenu.querySelectorAll('.cm-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const i = Number(btn.dataset.i);
      hideCtx();
      if (items[i] && items[i].act) items[i].act();
    });
  });
}

Editor.state.onContextMenu = (cx, cy, els) => {
  if (!els.length) { hideCtx(); return; }
  const hasGroup = els.some(e => e.gid);
  const firstGid = els[0].gid;
  const canGroup = els.length >= 2 && els.some(e => e.gid !== firstGid);
  const items = [];
  if (canGroup) items.push({ label: '组合为模块', act: () => { pushUndo(); Editor.groupSelected(); updateTip(); } });
  if (hasGroup) items.push({ label: '取消组合', act: () => { pushUndo(); Editor.ungroupSelected(); updateTip(); } });
  items.push({ label: '复制（Ctrl+D）', act: () => { pushUndo(); Editor.duplicateSelected(); updateTip(); } });
  items.push({ label: '置于顶层（Ctrl+]）', act: () => { pushUndo(); Editor.bringToFront(); updateTip(); } });
  items.push({ label: '置于底层（Ctrl+[）', act: () => { pushUndo(); Editor.sendToBack(); updateTip(); } });
  items.push({ label: '删除', danger: true, act: () => { pushUndo(); Editor.deleteSelected(); updateTip(); } });
  showCtx(cx, cy, items);
};

document.addEventListener('pointerdown', e => {
  if (!ctxMenu.hidden && !ctxMenu.contains(e.target)) hideCtx();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') hideCtx(); });
window.addEventListener('blur', hideCtx);
$('#canvas-wrap').addEventListener('wheel', hideCtx);
