/* ============================================================
 * elements.js — 元素目录、属性 Schema、参数化 SVG 渲染
 * 物理单位：所有道路以“米”建模，渲染尺寸 = 米 × PPM（12 px/m）
 * 标准依据：
 *   CJJ 193-2012 城市道路路线设计规范（车道宽 表5.3.1 / 圆曲线半径 表6.3.2）
 *   GB 5768 标志标线、GB 14887 信号灯、GB/T 24724 锥形交通路标
 *   GB 50647 / GB/T 36670 交叉口进口道宽度
 * ============================================================ */

/* ---------- 单位与色板 ---------- */
const PPM = 12;                 // 12 像素 = 1 米
const m = v => v * PPM;         // 米 → 像素

const C = {
  road: '#2b3442', roadLight: '#33404f', edge: '#4a5a70',
  white: '#e9f0f7', yellow: '#f5c542',
  signYellow: '#f5c542', signRed: '#d9343b', signBlue: '#1d6fe0',
  black: '#1c232c', orange: '#f27a1e',
  lampRed: '#ff4d4f', lampYellow: '#ffc531', lampGreen: '#3ddc84',
  housing: '#232c38'
};

/* ---------- 国标车道宽档位（一条机动车道） ---------- */
const LANE_W = [
  [3.75, '3.75 m · 高速/大型车 (v>60)'],
  [3.50, '3.50 m · 城市混行/标准 (v≤60)'],
  [3.25, '3.25 m · 小客车专用 (v≤60)'],
  [3.00, '3.00 m · 交叉口进口道'],
  [2.80, '2.80 m · 改建进口道极限']
];

/* ---------- 曲率半径档位（中心线半径 R，附曲率 κ=1/R） ---------- */
const R_OPTIONS = [20, 40, 70, 100, 150, 200, 300, 400, 650, 1000, 1600]
  .map(r => [r, `R=${r} m · κ=${(1 / r).toFixed(4)} /m`]);

/* ============================================================
 * 一、元素目录
 * ============================================================ */
const PALETTE = [
  {
    group: 'lane', label: '赛道 Lane',
    items: [
      { subtype: 'straight', label: '直道', w: 84, h: 144, props: { lanes: 2, laneW: 3.5, length_m: 12, twoWay: true } },
      { subtype: 'variable_lane', label: '可变车道', w: 168, h: 240, props: { lanesIn: 2, lanesOut: 4, laneW: 3.5, length_m: 20 } },
      { subtype: 'curve', label: '弯道', w: 140, h: 140, props: { lanes: 2, laneW: 3.5, Rc: 40, angle: 90, direction: 'right' } },
      { subtype: 'ramp', label: '匝道', w: 90, h: 90, props: { lanes: 1, laneW: 3.5, Rc: 40, angle: 90, direction: 'right' } },
      { subtype: 'roundabout', label: '环岛', w: 170, h: 170, props: { ringLanes: 2, laneW: 3.5, entries: 4, r0: 12 } },
      { subtype: 't_junction', label: '丁字路口', w: 160, h: 160, props: { mainLanes: 2, branchLanes: 1, laneW: 3.5, zebra: false } },
      { subtype: 'crossroads', label: '十字路口', w: 160, h: 160, props: { lanes: 2, laneW: 3.5, zebra: false } },
      { subtype: 'parking', label: '泊车位', w: 180, h: 140, props: { spaces: 4, stallW: 2.5, stallL: 5.3, aisleW: 6.0, layout: 'perpendicular' } }
    ]
  },
  {
    group: 'car', label: '车辆 Car',
    items: [
      { subtype: 'sedan', label: '轿车', w: 26, h: 46, props: { color: '#5eb8ff', mass: 1500, length_m: 4.7, width_m: 1.82, height_m: 1.45, max_speed: 180, max_accel: 3.0, max_decel: 8.0, turn_radius: 5.5, init_speed: 0, mode: 'L4' } },
      { subtype: 'suv', label: 'SUV', w: 28, h: 48, props: { color: '#7be0c3', mass: 1900, length_m: 4.85, width_m: 1.93, height_m: 1.78, max_speed: 190, max_accel: 2.8, max_decel: 7.5, turn_radius: 6.0, init_speed: 0, mode: 'L4' } },
      { subtype: 'truck', label: '卡车', w: 30, h: 64, props: { color: '#e8c46a', mass: 12000, length_m: 9.5, width_m: 2.5, height_m: 3.4, max_speed: 100, max_accel: 1.2, max_decel: 5.0, turn_radius: 9.0, init_speed: 0, mode: 'L2' } },
      { subtype: 'bus', label: '巴士', w: 30, h: 66, props: { color: '#8fd0ff', mass: 13500, length_m: 10.5, width_m: 2.5, height_m: 3.2, max_speed: 90, max_accel: 1.3, max_decel: 5.5, turn_radius: 10.0, init_speed: 0, mode: 'L2' } },
      { subtype: 'two_wheeler', label: '两轮车', w: 16, h: 38, props: { color: '#f0946b', mass: 160, length_m: 2.0, width_m: 0.75, height_m: 1.1, max_speed: 80, max_accel: 3.5, max_decel: 7.0, turn_radius: 2.5, init_speed: 0, mode: 'manual' } },
      { subtype: 'pedestrian', label: '行人', w: 10, h: 22, props: { shirt: '#4a90d9', pose: 'walk' } }
    ]
  },
  {
    group: 'sign', label: 'GB交通标志',
    items: [
      { subtype: 'warn_danger', label: '注意危险', w: 46, h: 46, props: {} },
      { subtype: 'warn_pedestrian', label: '注意行人', w: 46, h: 46, props: {} },
      { subtype: 'warn_children', label: '注意儿童', w: 46, h: 46, props: {} },
      { subtype: 'warn_signal', label: '注意信号灯', w: 46, h: 46, props: {} },
      { subtype: 'warn_cross', label: '十字交叉', w: 46, h: 46, props: {} },
      { subtype: 'warn_bend_l', label: '向左急弯', w: 46, h: 46, props: {} },
      { subtype: 'warn_bend_r', label: '向右急弯', w: 46, h: 46, props: {} },
      { subtype: 'warn_slow', label: '慢行', w: 46, h: 46, props: {} },
      { subtype: 'warn_work', label: '施工', w: 46, h: 46, props: {} },
      { subtype: 'ban_no_entry', label: '禁止驶入', w: 44, h: 44, props: {} },
      { subtype: 'ban_no_motor', label: '禁机动车', w: 44, h: 44, props: {} },
      { subtype: 'ban_speed', label: '限制速度', w: 44, h: 44, props: { limit: 40 } },
      { subtype: 'ban_no_park', label: '禁止停车', w: 44, h: 44, props: {} },
      { subtype: 'ban_no_horn', label: '禁止鸣笛', w: 44, h: 44, props: {} },
      { subtype: 'ban_no_uturn', label: '禁止掉头', w: 44, h: 44, props: {} },
      { subtype: 'ban_stop', label: '停车让行', w: 48, h: 48, props: {} },
      { subtype: 'ban_give_way', label: '减速让行', w: 48, h: 48, props: {} },
      { subtype: 'ind_straight', label: '直行', w: 44, h: 44, props: {} },
      { subtype: 'ind_turn_l', label: '向左转弯', w: 44, h: 44, props: {} },
      { subtype: 'ind_turn_r', label: '向右转弯', w: 44, h: 44, props: {} },
      { subtype: 'ind_crosswalk', label: '人行横道', w: 44, h: 44, props: {} },
      { subtype: 'ind_motor', label: '机动车行驶', w: 44, h: 44, props: {} },
      { subtype: 'ind_parking', label: '停车位', w: 44, h: 44, props: {} }
    ]
  },
  {
    group: 'obstacle', label: '障碍物',
    items: [
      { subtype: 'cone', label: '雪糕筒', w: 24, h: 28, props: {} },
      { subtype: 'water_barrier', label: '水马', w: 46, h: 28, props: {} },
      { subtype: 'crash_barrel', label: '防撞桶', w: 34, h: 36, props: {} },
      { subtype: 'guardrail', label: '波形护栏', w: 96, h: 22, props: {} },
      { subtype: 'fence', label: '施工围挡', w: 96, h: 32, props: {} },
      { subtype: 'beacon', label: '警示灯', w: 24, h: 28, props: {} },
      { subtype: 'free_obstacle', label: '自由障碍物', w: 120, h: 120, props: { width_m: 10, depth_m: 10, color: '#d9343b', label: '' } }
    ]
  },
  {
    group: 'light', label: '交通信号灯',
    items: [
      { subtype: 'light_vehicle', label: '机动车信号灯', w: 28, h: 74, props: { active: 'green' } },
      { subtype: 'light_arrow', label: '方向信号灯', w: 28, h: 74, props: { active: 'green' } },
      { subtype: 'light_flash', label: '闪光警告灯', w: 28, h: 30, props: {} },
      { subtype: 'light_lane', label: '车道信号灯', w: 66, h: 30, props: { active: 'green' } }
    ]
  }
];

/* 车辆默认运动参数：直线移动默认关闭，速度 30 km/h、前进 50 m */
const MOVE_DEFAULTS = { move: false, moveSpeed: 30, moveDistance: 50 };
PALETTE.forEach(g => {
  if (g.group === 'car') g.items.forEach(it => {
    if (it.subtype !== 'pedestrian') Object.assign(it.props, MOVE_DEFAULTS);
  });
});

const CAR_SUBTYPES = new Set(
  PALETTE.find(g => g.group === 'car').items.filter(i => i.subtype !== 'pedestrian').map(i => i.subtype));

/* 兼容旧 JSON：为车辆补齐直线移动默认属性 */
function ensureCarProps(el) {
  if (el.type === 'car' && CAR_SUBTYPES.has(el.subtype)) {
    el.props = Object.assign({}, MOVE_DEFAULTS, el.props || {});
  }
  return el;
}

const CATALOG_MAP = {};
PALETTE.forEach(g => g.items.forEach(it => {
  CATALOG_MAP[it.subtype] = Object.assign({ type: g.group }, it);
}));

/* ============================================================
 * 二、属性 Schema
 * ============================================================ */
const INSPECTOR_SCHEMA = {
  straight: [{
    section: '直道参数', fields: [
      { key: 'lanes', label: '车道数', type: 'number', min: 1, max: 8, step: 1, resize: true },
      { key: 'laneW', label: '车道宽度（国标）', type: 'select', options: LANE_W, resize: true },
      { key: 'length_m', label: '长度', unit: 'm', type: 'number', min: 5, max: 200, step: 1, resize: true },
    { key: 'twoWay', label: '双向通行', type: 'check' }
    ]
  }],
  variable_lane: [{
    section: '可变车道参数（入口→出口）', fields: [
      { key: 'lanesIn', label: '入口车道数', type: 'number', min: 1, max: 8, step: 1, resize: true },
      { key: 'lanesOut', label: '出口车道数', type: 'number', min: 1, max: 8, step: 1, resize: true },
      { key: 'laneW', label: '车道宽度（国标）', type: 'select', options: LANE_W, resize: true },
      { key: 'length_m', label: '渐变段长度', unit: 'm', type: 'number', min: 5, max: 200, step: 1, resize: true }
    ]
  }],
  curve: [{
    section: '弯道参数', fields: [
      { key: 'lanes', label: '车道数', type: 'number', min: 1, max: 6, step: 1, resize: true },
      { key: 'laneW', label: '车道宽度（国标）', type: 'select', options: LANE_W, resize: true },
      { key: 'Rc', label: '中心线半径（曲率 κ=1/R）', unit: 'm', type: 'number', min: 10, max: 2000, step: 1, resize: true },
      { key: 'angle', label: '弧度（转角）', unit: '°', type: 'number', min: 1, max: 360, step: 1, resize: true },
      { key: 'direction', label: '转弯方向', type: 'select', options: [['right', '右转'], ['left', '左转']] }
    ]
  }],
  ramp: [{
    section: '匝道参数', fields: [
      { key: 'lanes', label: '车道数', type: 'number', min: 1, max: 2, step: 1, resize: true },
      { key: 'laneW', label: '车道宽度（国标）', type: 'select', options: LANE_W, resize: true },
      { key: 'Rc', label: '中心线半径（曲率 κ=1/R）', unit: 'm', type: 'number', min: 10, max: 2000, step: 1, resize: true },
      { key: 'angle', label: '弧度（转角）', unit: '°', type: 'number', min: 1, max: 360, step: 1, resize: true },
      { key: 'direction', label: '转弯方向', type: 'select', options: [['right', '右转'], ['left', '左转']] }
    ]
  }],
  roundabout: [{
    section: '环岛参数', fields: [
      { key: 'ringLanes', label: '环道车道数', type: 'number', min: 1, max: 5, step: 1, resize: true },
      { key: 'laneW', label: '车道宽度（国标）', type: 'select', options: LANE_W, resize: true },
      { key: 'r0', label: '中心岛半径', unit: 'm', type: 'number', min: 5, max: 40, step: 1, resize: true },
      { key: 'entries', label: '入口数量', type: 'select', options: [[3, '3 个入口'], [4, '4 个入口']] }
    ]
  }],
  t_junction: [{
    section: '丁字路口参数', fields: [
      { key: 'mainLanes', label: '主路每方向车道数', type: 'number', min: 1, max: 5, step: 1, resize: true },
      { key: 'branchLanes', label: '支路车道数', type: 'number', min: 1, max: 5, step: 1, resize: true },
      { key: 'laneW', label: '车道宽度（国标）', type: 'select', options: LANE_W, resize: true },
      { key: 'zebra', label: '显示斑马线', type: 'check' }
    ]
  }],
  crossroads: [{
    section: '十字路口参数', fields: [
      { key: 'lanes', label: '每方向车道数', type: 'number', min: 1, max: 4, step: 1, resize: true },
      { key: 'laneW', label: '车道宽度（国标）', type: 'select', options: LANE_W, resize: true },
      { key: 'zebra', label: '显示斑马线', type: 'check' }
    ]
  }],
  parking: [{
    section: '泊车位参数（国标单个车位）', fields: [
      { key: 'spaces', label: '车位数量', type: 'number', min: 1, max: 20, step: 1, resize: true },
      { key: 'stallW', label: '单个车位宽度', unit: 'm', type: 'number', min: 2.2, max: 3.5, step: 0.05, resize: true },
      { key: 'stallL', label: '单个车位长度', unit: 'm', type: 'number', min: 4.5, max: 7.0, step: 0.1, resize: true },
      { key: 'aisleW', label: '通道宽度', unit: 'm', type: 'number', min: 3.0, max: 9.0, step: 0.1, resize: true },
      { key: 'layout', label: '停车方式', type: 'select', options: [['perpendicular', '垂直式（垂直通道）'], ['parallel', '平行式（平行通道）']] }
    ]
  }],
  pedestrian: [{
    section: '行人参数', fields: [
      { key: 'shirt', label: '上衣颜色', type: 'color' },
      { key: 'pose', label: '姿态', type: 'select', options: [['walk', '行走'], ['stand', '站立']] }
    ]
  }],
  _vehicle: [
    { section: '外观', fields: [{ key: 'color', label: '车身颜色', type: 'color' }] },
    {
      section: '直线移动预设', fields: [
        { key: 'move', label: '启用直线移动', type: 'check' },
        { key: 'moveSpeed', label: '前进速度', unit: 'km/h', type: 'number', min: 0, max: 220, step: 5 },
        { key: 'moveDistance', label: '前进距离（沿车头方向）', unit: 'm', type: 'number', min: 1, max: 500, step: 1 }
      ]
    },
    {
      section: '动力学参数', fields: [
        { key: 'mass', label: '整车质量', unit: 'kg', type: 'number', min: 50, max: 40000, step: 10 },
        { key: 'length_m', label: '车长', unit: 'm', type: 'number', min: 1, max: 18, step: 0.1 },
        { key: 'width_m', label: '车宽', unit: 'm', type: 'number', min: 0.5, max: 3.5, step: 0.05 },
        { key: 'height_m', label: '车高', unit: 'm', type: 'number', min: 0.8, max: 4.5, step: 0.05 },
        { key: 'max_speed', label: '最高速度', unit: 'km/h', type: 'number', min: 20, max: 220, step: 5 },
        { key: 'max_accel', label: '最大加速度', unit: 'm/s²', type: 'number', min: 0.2, max: 8, step: 0.1 },
        { key: 'max_decel', label: '最大减速度', unit: 'm/s²', type: 'number', min: 1, max: 12, step: 0.1 },
        { key: 'turn_radius', label: '最小转弯半径', unit: 'm', type: 'number', min: 1.5, max: 15, step: 0.1 },
        { key: 'init_speed', label: '初始速度', unit: 'km/h', type: 'number', min: 0, max: 120, step: 1 },
        { key: 'mode', label: '驾驶模式', type: 'select', options: [['L4', '自动驾驶 L4'], ['L2', '辅助驾驶 L2'], ['manual', '人工驾驶']] }
      ]
    }
  ],
  ban_speed: [{ section: '禁令参数', fields: [{ key: 'limit', label: '限速值', unit: 'km/h', type: 'number', min: 5, max: 120, step: 5 }] }],
  light_vehicle: [{ section: '信号灯状态', fields: [{ key: 'active', label: '点亮灯色', type: 'select', options: [['red', '红灯'], ['yellow', '黄灯'], ['green', '绿灯']] }] }],
  light_arrow: [{ section: '信号灯状态', fields: [{ key: 'active', label: '点亮灯色', type: 'select', options: [['red', '红灯'], ['yellow', '黄灯'], ['green', '绿灯']] }] }],
  light_lane: [{ section: '信号灯状态', fields: [{ key: 'active', label: '点亮状态', type: 'select', options: [['green', '绿色箭头(通行)'], ['red', '红色叉形(禁行)']] }] }],
  free_obstacle: [{
    section: '自由障碍物参数', fields: [
      { key: 'width_m', label: '宽度', unit: 'm', type: 'number', min: 0.1, max: 500, step: 0.1, resize: true },
      { key: 'depth_m', label: '纵深（长度）', unit: 'm', type: 'number', min: 0.1, max: 500, step: 0.1, resize: true },
      { key: 'color', label: '填充颜色', type: 'color' },
      { key: 'label', label: '标注文字', type: 'text' }
    ]
  }]
};

function schemaOf(subtype, type) {
  if (INSPECTOR_SCHEMA[subtype]) return INSPECTOR_SCHEMA[subtype];
  if (type === 'car') return INSPECTOR_SCHEMA._vehicle;
  return [];
}

/* ============================================================
 * 三、尺寸推导（物理单位 → 像素）
 * ============================================================ */
function sizeFromProps(el) {
  const p = el.props, s = el.subtype;
  if (s === 'straight') return { w: m(p.lanes * p.laneW), h: m(p.length_m) };
  if (s === 'variable_lane') {
    // 包围盒取入口/出口中较宽者，保证渐变段不被裁切
    return { w: m(Math.max(Number(p.lanesIn) || 1, Number(p.lanesOut) || 1) * Number(p.laneW)), h: m(p.length_m) };
  }
  if (s === 'curve' || s === 'ramp') { const g = arcGeo(el); return { w: g.w, h: g.h }; }
  if (s === 'roundabout') {
    const Spx = m(2 * (p.r0 + p.ringLanes * p.laneW + 6));
    return { w: Spx, h: Spx };
  }
  if (s === 't_junction' || s === 'crossroads') return { w: m(30), h: m(30) };
  if (s === 'parking') {
    const perp = p.layout !== 'parallel';
    const Wm = perp ? p.spaces * p.stallW : p.spaces * p.stallL;
    const Hm = perp ? p.stallL + p.aisleW : p.stallW + p.aisleW;
    return { w: m(Wm), h: m(Hm) };
  }
  if (s === 'free_obstacle') {
    return { w: m(Number(p.width_m) || 10), h: m(Number(p.depth_m) || 10) };
  }
  return { w: el.w, h: el.h };
}

/* ============================================================
 * 四、渲染入口
 * ============================================================ */
/* 车辆直线移动轨迹：沿车头方向(-y)按距离绘制虚线与终点标记 */
function movementMarkup(el) {
  const p = el.props;
  if (!p.move || !CAR_SUBTYPES.has(el.subtype)) return '';
  const dist = m(Number(p.moveDistance) || 0);
  if (dist <= 0) return '';
  const y0 = -el.h / 2 - 8, y1 = y0 - dist;
  let out = line(0, y0, 0, y1, C.yellow, 2, '7 6');
  out += `<path d="M0 ${r3(y1)} L-5 ${r3(y1 + 9)} L5 ${r3(y1 + 9)} Z" fill="${C.yellow}"/>`;
  out += `<text x="8" y="${r3((y0 + y1) / 2)}" font-size="12" fill="${C.yellow}">${p.moveSpeed} km/h · ${p.moveDistance} m</text>`;
  return out;
}

function shapeMarkup(el) {
  let out = RENDER[el.subtype] ? RENDER[el.subtype](el) : '';
  out += movementMarkup(el);
  return out;
}
function previewMarkup(subtype) {
  const cat = CATALOG_MAP[subtype];
  return shapeMarkup({ subtype, type: cat.type, w: cat.w, h: cat.h, props: cat.props });
}
function previewThumb(subtype) {
  const cat = CATALOG_MAP[subtype];
  const k = 36 / Math.max(cat.w, cat.h);
  return `<svg viewBox="${-cat.w / 2} ${-cat.h / 2} ${cat.w} ${cat.h}" width="${Math.max(8, cat.w * k)}" height="${Math.max(8, cat.h * k)}">${previewMarkup(subtype)}</svg>`;
}

const RENDER = {};
const PORTS = {};

/* ============================================================
 * 五、赛道几何
 * ============================================================ */

/* 直道（纵向沿 y 轴） */
RENDER.straight = el => {
  const { w, h } = el, p = el.props, lwpx = m(p.laneW);
  let out = rect(-w / 2, -h / 2, w, h, C.road);
  out += line(-w / 2 + 1.5, -h / 2, -w / 2 + 1.5, h / 2, C.white, 1.6);
  out += line(w / 2 - 1.5, -h / 2, w / 2 - 1.5, h / 2, C.white, 1.6);
  if (p.twoWay) {
    if (p.centerLine === 'dashed') {
      out += dashLine(0, -h / 2, 0, h / 2);
    } else {
      out += line(-2.2, -h / 2, -2.2, h / 2, C.yellow, 1.6);
      out += line(2.2, -h / 2, 2.2, h / 2, C.yellow, 1.6);
    }
    for (let i = 1; i < p.lanes / 2; i++) {
      out += dashLine(-i * lwpx, -h / 2, -i * lwpx, h / 2);
      out += dashLine(i * lwpx, -h / 2, i * lwpx, h / 2);
    }
  } else {
    for (let i = 1; i < p.lanes; i++) out += dashLine(-w / 2 + i * lwpx, -h / 2, -w / 2 + i * lwpx, h / 2);
  }
  return out;
};
PORTS.straight = el => [
  { x: 0, y: -el.h / 2, normal: -90, width: el.w },
  { x: 0, y: el.h / 2, normal: 90, width: el.w }
];

/* 可变车道：上端入口(lanesIn)、下端出口(lanesOut)
 * GB 5768.3：车道分界线为平行于行车方向的白色直线虚线，仅车道边缘线在渐变区平滑过渡；
 * 渐变段只占全长中段，两端保持平直路段。虚线不随车道数变化产生斜率。 */
RENDER.variable_lane = el => {
  const { h } = el, p = el.props;
  const lwpx = m(Number(p.laneW));
  const nIn = Math.max(1, Math.round(Number(p.lanesIn) || 1));
  const nOut = Math.max(1, Math.round(Number(p.lanesOut) || 1));
  const win = nIn * lwpx, wout = nOut * lwpx;
  const yT = -h / 2, yB = h / 2;
  const yA = yT + h * 0.30, yBt = yB - h * 0.30;   // 渐变起止（两端各留 30% 平直段）
  const kg = (yBt - yA) * 0.38;                    // 边缘曲线控制点偏移

  // 路面轮廓：平直段 + 中段贝塞尔渐变 + 平直段
  const outline = [
    `M${r3(-win / 2)} ${r3(yT)}`,
    `L${r3(-win / 2)} ${r3(yA)}`,
    `C${r3(-win / 2)} ${r3(yA + kg)} ${r3(-wout / 2)} ${r3(yBt - kg)} ${r3(-wout / 2)} ${r3(yBt)}`,
    `L${r3(-wout / 2)} ${r3(yB)}`,
    `L${r3(wout / 2)} ${r3(yB)}`,
    `L${r3(wout / 2)} ${r3(yBt)}`,
    `C${r3(wout / 2)} ${r3(yBt - kg)} ${r3(win / 2)} ${r3(yA + kg)} ${r3(win / 2)} ${r3(yA)}`,
    `L${r3(win / 2)} ${r3(yT)}`, 'Z'
  ].join(' ');
  let out = `<path d="${outline}" fill="${C.road}" stroke="${C.edge}" stroke-width="1"/>`;

  // 两侧车道边缘线（实线）：平直段 + 渐变曲线 + 平直段
  const edge = (xT, xB) => [
    `M${r3(xT)} ${r3(yT)}`,
    `L${r3(xT)} ${r3(yA)}`,
    `C${r3(xT)} ${r3(yA + kg)} ${r3(xB)} ${r3(yBt - kg)} ${r3(xB)} ${r3(yBt)}`,
    `L${r3(xB)} ${r3(yB)}`
  ].join(' ');
  out += `<path d="${edge(-win / 2 + 1.5, -wout / 2 + 1.5)}" fill="none" stroke="${C.white}" stroke-width="1.6"/>`;
  out += `<path d="${edge(win / 2 - 1.5, wout / 2 - 1.5)}" fill="none" stroke="${C.white}" stroke-width="1.6"/>`;

  // 车道分界线：国标为平行于行车方向的直线虚线，不随边缘弯曲，也不产生斜率。
  // 入口分界集合 Xin、出口分界集合 Xout：两侧共有的分界贯穿全长；
  // 仅入口侧有的止于渐变终点 yBt（出口边缘实线处），仅出口侧有的始于渐变起点 yA（入口边缘实线处），
  // 使虚线始终延伸到实线边界，不在路面中途断掉。
  const EPS = 0.01;
  const xIn = [], xOut = [];
  for (let i = 1; i < nIn; i++) xIn.push(-win / 2 + i * lwpx);
  for (let j = 1; j < nOut; j++) xOut.push(-wout / 2 + j * lwpx);
  for (const x of xIn) {
    const yEnd = xOut.some(v => Math.abs(v - x) < EPS) ? yB : yBt;
    out += dashLine(x, yT, x, yEnd);
  }
  for (const x of xOut) {
    if (!xIn.some(v => Math.abs(v - x) < EPS)) out += dashLine(x, yA, x, yB);
  }
  // 车流方向提示（入口 → 出口）
  out += `<path d="M-5 -2 L0 4 L5 -2" fill="none" stroke="${C.white}" stroke-width="1.6" opacity="0.85"/>`;
  return out;
};
PORTS.variable_lane = el => {
  const p = el.props, lwpx = m(Number(p.laneW));
  const win = Math.max(1, Number(p.lanesIn) || 1) * lwpx;
  const wout = Math.max(1, Number(p.lanesOut) || 1) * lwpx;
  return [
    { x: 0, y: -el.h / 2, normal: -90, width: win },
    { x: 0, y: el.h / 2, normal: 90, width: wout }
  ];
};

/* 弯道 / 匝道几何（圆心坐标系，再平移到包围盒中心） */
function arcGeo(el) {
  const p = el.props;
  // 全部强制 Number，防止字符串拼接（下拉值或旧 JSON 可能是字符串）
  const lanesN = Number(p.lanes), laneW = Number(p.laneW);
  const Rc = Number(p.Rc), angle = Number(p.angle);
  const Wm = lanesN * laneW;
  const rm = Rc - Wm / 2, Rm = Rc + Wm / 2;
  const a = angle * Math.PI / 180;
  const sgn = p.direction === 'right' ? -1 : 1;
  const a0 = -Math.PI / 2, a1 = -Math.PI / 2 + sgn * a;
  const Rpx = m(Rm), rpx = m(rm), Rcpx = m(Rc), lwpx = m(laneW);
  const swOut = p.direction === 'right' ? 0 : 1, swIn = 1 - swOut;

  const P1 = [Rpx * Math.cos(a0), Rpx * Math.sin(a0)];
  const P2 = [Rpx * Math.cos(a1), Rpx * Math.sin(a1)];
  const Q1 = [rpx * Math.cos(a0), rpx * Math.sin(a0)];
  const Q2 = [rpx * Math.cos(a1), rpx * Math.sin(a1)];

  const xmin = Math.min(P1[0], P2[0], Q1[0], Q2[0]);
  const xmax = Math.max(P1[0], P2[0], Q1[0], Q2[0]);
  const ymin = Math.min(P1[1], P2[1], Q1[1], Q2[1]);
  const ymax = Math.max(P1[1], P2[1], Q1[1], Q2[1]);
  const w = xmax - xmin, h = ymax - ymin;
  const ox = -(xmin + xmax) / 2, oy = -(ymin + ymax) / 2;

  const road = `<path d="M${r3(P1[0])} ${r3(P1[1])} A${r3(Rpx)} ${r3(Rpx)} 0 0 ${swOut} ${r3(P2[0])} ${r3(P2[1])} L${r3(Q2[0])} ${r3(Q2[1])} A${r3(rpx)} ${r3(rpx)} 0 0 ${swIn} ${r3(Q1[0])} ${r3(Q1[1])} Z" fill="${C.road}" stroke="${C.edge}" stroke-width="1"/>`;
  let lanes = '';
  for (let i = 1; i < lanesN; i++) {
    const rho = rpx + i * lwpx;
    const u1 = [rho * Math.cos(a0), rho * Math.sin(a0)];
    const u2 = [rho * Math.cos(a1), rho * Math.sin(a1)];
    lanes += `<path d="M${r3(u1[0])} ${r3(u1[1])} A${r3(rho)} ${r3(rho)} 0 0 ${swOut} ${r3(u2[0])} ${r3(u2[1])}" fill="none" stroke="${C.white}" stroke-width="1.4" stroke-dasharray="9 8"/>`;
  }
  const c1 = [Rcpx * Math.cos(a0) + ox, Rcpx * Math.sin(a0) + oy];
  const c2 = [Rcpx * Math.cos(a1) + ox, Rcpx * Math.sin(a1) + oy];
  const ports = [
    { x: c1[0], y: c1[1], normal: a0 * 180 / Math.PI, width: m(Wm) },
    { x: c2[0], y: c2[1], normal: a1 * 180 / Math.PI, width: m(Wm) }
  ];
  return { w, h, ox, oy, road, lanes, Rpx, ports };
}

function arcMarkup(el, isRamp) {
  const g = arcGeo(el);
  return `<g transform="translate(${r3(g.ox)},${r3(g.oy)})">${g.road}${g.lanes}</g>`;
}
RENDER.curve = el => arcMarkup(el, false);
RENDER.ramp = el => arcMarkup(el, true);
PORTS.curve = el => arcGeo(el).ports;
PORTS.ramp = el => arcGeo(el).ports;

/* 环岛 */
RENDER.roundabout = el => {
  const p = el.props;
  const r0 = Number(p.r0), ringLanes = Number(p.ringLanes), laneW = Number(p.laneW);
  const ringWm = ringLanes * laneW, Rm = r0 + ringWm;
  const Rmpx = m(Rm), r0px = m(r0);
  const Spx = m(2 * (Rm + 6)), half = Spx / 2, ew = m(2 * laneW);   // 出入口为双车道
  const dirs = Number(p.entries) === 3 ? ['top', 'right', 'left'] : ['top', 'right', 'bottom', 'left'];
  let out = '';
  dirs.forEach(d => {
    if (d === 'top') out += rect(-ew / 2, -half, ew, half - Rmpx, C.road);
    if (d === 'bottom') out += rect(-ew / 2, Rmpx, ew, half - Rmpx, C.road);
    if (d === 'left') out += rect(-half, -ew / 2, half - Rmpx, ew, C.road);
    if (d === 'right') out += rect(Rmpx, -ew / 2, half - Rmpx, ew, C.road);
  });
  out += circle(0, 0, Rmpx, C.road);
  for (let i = 1; i < ringLanes; i++) {
    out += circle(0, 0, m(r0) + m(laneW) * i, 'none', C.white, 1.3, '8 7');
  }
  out += circle(0, 0, r0px, '#3a4a5f', C.white, 2);
  out += circle(0, 0, r0px * 0.55, '#46586e');
  return out;
};
PORTS.roundabout = el => {
  const half = el.w / 2, ew = m(2 * el.props.laneW);   // 出入口双车道宽
  const all = [
    { x: 0, y: -half, normal: -90, width: ew },
    { x: half, y: 0, normal: 0, width: ew },
    { x: 0, y: half, normal: 90, width: ew },
    { x: -half, y: 0, normal: 180, width: ew }
  ];
  return el.props.entries === 3 ? all.filter((_, i) => i !== 2) : all;
};

/* 丁字路口（主路横向，支路自上接入） */
RENDER.t_junction = el => {
  const p = el.props, Spx = m(30), half = Spx / 2, lwpx = m(p.laneW);
  const Wmainpx = m(2 * p.mainLanes * p.laneW), Wbpx = m(p.branchLanes * p.laneW);
  const hmw = Wmainpx / 2, hbw = Wbpx / 2;
  let out = rect(-half, -hmw, Spx, Wmainpx, C.road);
  out += rect(-hbw, -half, Wbpx, half + hmw, C.road);
  // 右转专用车道铺装（先于标线，避免盖住引导线）
  const um = -hmw + lwpx / 2, ub = -hbw + lwpx / 2, vb = -ub;
  out += rightTurnLane(-half, -half, ub, -half, -half, um, lwpx);
  out += rightTurnLane(half, -half, half, um, vb, -half, lwpx);
  for (let i = 1; i < 2 * p.mainLanes; i++) {
    const y = -hmw + i * lwpx;
    out += dashLine(-half, y, -hbw, y);
    out += dashLine(hbw, y, half, y);
  }
  // 支路引导线：双向中线（黄色双实线）+ 同向车道分界虚线，画到主路北缘为止
  out += line(-2.2, -half, -2.2, -hmw, C.yellow, 1.6);
  out += line(2.2, -half, 2.2, -hmw, C.yellow, 1.6);
  for (let i = 1; i < p.branchLanes / 2; i++) {
    out += dashLine(-i * lwpx, -half, -i * lwpx, -hmw);
    out += dashLine(i * lwpx, -half, i * lwpx, -hmw);
  }
  // 主路南侧车道边缘实线（贯通；北侧与支路两侧由右转匝道外侧弧线承担，避免直角）
  out += line(-half, hmw, half, hmw, C.white, 1.6);
  const sy = -hmw - 5;
  out += line(-hbw + 2, sy, hbw - 2, sy, C.white, 2);
  if (p.zebra) out += zebra(-hbw + 3, sy - 3 - 36, Wbpx - 6, 36, 'h');
  return out;
};
PORTS.t_junction = el => {
  const half = m(15), Wmainpx = m(2 * p_main(el) * el.props.laneW), Wbpx = m(el.props.branchLanes * el.props.laneW);
  return [
    { x: -half, y: 0, normal: 180, width: Wmainpx },
    { x: half, y: 0, normal: 0, width: Wmainpx },
    { x: 0, y: -half, normal: -90, width: Wbpx }
  ];
};
function p_main(el) { return el.props.mainLanes; }

/* 十字路口（多车道） */
RENDER.crossroads = el => {
  const p = el.props, Spx = m(30), half = Spx / 2, lwpx = m(p.laneW);
  const Wpx = m(2 * p.lanes * p.laneW), hw = Wpx / 2;
  let out = rect(-half, -hw, Spx, Wpx, C.road);
  out += rect(-hw, -half, Wpx, Spx, C.road);
  for (let i = 1; i < 2 * p.lanes; i++) {
    const d = -hw + i * lwpx;
    out += dashLine(-half, d, -hw, d);
    out += dashLine(hw, d, half, d);
    out += dashLine(d, -half, d, -hw);
    out += dashLine(d, hw, d, half);
  }
  // 四个进口最外侧车道边缘由右转匝道外侧弧线承担，不再画直角直线
  [[-hw, -hw - 5, hw, -hw - 5],
  [-hw, hw + 5, hw, hw + 5],
  [-hw - 5, -hw, -hw - 5, hw],
  [hw + 5, -hw, hw + 5, hw]].forEach(s => {
    out += line(s[0], s[1], s[2], s[3], C.white, 2);
  });
  const ay = (hw + 5 + half) / 2;
  out += guideArrow(0, -ay, 180) + guideArrow(0, ay, 0) +
    guideArrow(-ay, 0, 90) + guideArrow(ay, 0, -90);
  // 右转专用车道：标准一车道椭圆环带（右侧通行）
  const u = -hw + lwpx / 2, v = -u;
  out += rightTurnLane(-half, -half, u, -half, -half, u, lwpx);
  out += rightTurnLane(-half, half, -half, v, u, half, lwpx);
  out += rightTurnLane(half, half, v, half, half, v, lwpx);
  out += rightTurnLane(half, -half, half, u, v, -half, lwpx);
  if (p.zebra) {
    const zW = Wpx - 6, zD = 36, gap = 3;
    out += zebra(-hw + 3, -hw - 5 - gap - zD, zW, zD, 'h');
    out += zebra(-hw + 3, hw + 5 + gap, zW, zD, 'h');
    out += zebra(-hw - 5 - gap - zD, -hw + 3, zD, zW, 'v');
    out += zebra(hw + 5 + gap, -hw + 3, zD, zW, 'v');
  }
  return out;
};
PORTS.crossroads = el => {
  const half = m(15), Wpx = m(2 * el.props.lanes * el.props.laneW);
  return [
    { x: 0, y: -half, normal: -90, width: Wpx },
    { x: half, y: 0, normal: 0, width: Wpx },
    { x: 0, y: half, normal: 90, width: Wpx },
    { x: -half, y: 0, normal: 180, width: Wpx }
  ];
};

/* 导向小箭头（白色，dir 为箭头指向角度） */
function guideArrow(x, y, dir) {
  return `<g transform="translate(${r3(x)},${r3(y)}) rotate(${dir})">
    <path d="M0 -8 L-3.4 -2.6 L-1.4 -2.6 L-1.4 5 L1.4 5 L1.4 -2.6 L3.4 -2.6 Z" fill="#dfe9f4"/>
  </g>`;
}

/* 右转专用车道（标准一车道）：以路口角为圆心的四分之一椭圆环带 + 外侧边缘实线
 * (cx,cy)=路口角圆心；(px,py)=进口最右车道中心；(qx,qy)=出口最右车道中心 */
function rightTurnLane(cx, cy, px, py, qx, qy, lanePx) {
  const h = lanePx / 2;
  const dx = px - cx, dy = py - cy, ex = qx - cx, ey = qy - cy;
  const rx = Math.abs(dx) + Math.abs(ex), ry = Math.abs(dy) + Math.abs(ey);
  // 点落在 x 轴时按 rx 收缩/扩张，落在 y 轴时按 ry（原实现混用导致进路口匝道偏移）
  const point = (vx, vy, outer) => {
    const inX = Math.abs(vy) < 0.001;
    const r = (inX ? rx : ry) + (outer ? -h : h);
    return inX ? [cx + Math.sign(vx || 1) * r, cy] : [cx, cy + Math.sign(vy || 1) * r];
  };
  const [xo0, yo0] = point(dx, dy, true), [xo1, yo1] = point(ex, ey, true);
  const [xi0, yi0] = point(dx, dy, false), [xi1, yi1] = point(ex, ey, false);
  const rxO = rx - h, ryO = ry - h, rxI = rx + h, ryI = ry + h;
  const band = `M${r3(xo0)} ${r3(yo0)} A${r3(rxO)} ${r3(ryO)} 0 0 1 ${r3(xo1)} ${r3(yo1)} L${r3(xi1)} ${r3(yi1)} A${r3(rxI)} ${r3(ryI)} 0 0 0 ${r3(xi0)} ${r3(yi0)} Z`;
  // 外侧边缘恒为实线
  const outerEdge = `M${r3(xo0)} ${r3(yo0)} A${r3(rxO)} ${r3(ryO)} 0 0 1 ${r3(xo1)} ${r3(yo1)}`;
  // 内侧为直道车道分界线的延伸，用虚线
  const innerEdge = `M${r3(xi0)} ${r3(yi0)} A${r3(rxI)} ${r3(ryI)} 0 0 1 ${r3(xi1)} ${r3(yi1)}`;
  return `<path d="${band}" fill="${C.road}" stroke="none"/>` +
    `<path d="${outerEdge}" fill="none" stroke="${C.white}" stroke-width="1.6"/>` +
    `<path d="${innerEdge}" fill="none" stroke="${C.white}" stroke-width="1.6" stroke-dasharray="9 8"/>`;
}

/* 泊车位（按国标单个车位尺寸建模，整体尺寸由数量×单车位+通道推导，不再均分固定区域） */
RENDER.parking = el => {
  const { w, h } = el, p = el.props;
  const perp = p.layout !== 'parallel';
  const stallWpx = m(p.stallW), stallLpx = m(p.stallL), aisleWpx = m(p.aisleW);
  let out = rect(-w / 2, -h / 2, w, h, '#26303d', C.edge, 1.2);

  if (perp) {
    // 垂直式：车位在上方（纵深=车位长 stallL），通道在下方（高 aisleW）
    const top = -h / 2, bottom = top + stallLpx;
    out += line(-w / 2, bottom, w / 2, bottom, C.white, 1.6);
    out += line(-w / 2, top, w / 2, top, C.white, 1.4);
    for (let i = 1; i < p.spaces; i++) out += line(-w / 2 + i * stallWpx, top, -w / 2 + i * stallWpx, bottom, C.white, 1.4);
    for (let i = 0; i < p.spaces; i++) {
      const cx = -w / 2 + i * stallWpx + stallWpx / 2;
      out += rect(cx - stallWpx * 0.32, bottom - 4, stallWpx * 0.64, 3.2, '#5a6b82');   // 挡车器
    }
    out += aisleLabel(0, bottom + aisleWpx / 2, p.aisleW);
  } else {
    // 平行式：车位沿上方横向排列（每个车位长 stallL、宽 stallW），通道在下方
    const top = -h / 2, bottom = top + stallWpx;
    out += line(-w / 2, bottom, w / 2, bottom, C.white, 1.6);
    out += line(-w / 2, top, w / 2, top, C.white, 1.4);
    for (let i = 1; i < p.spaces; i++) out += line(-w / 2 + i * stallLpx, top, -w / 2 + i * stallLpx, bottom, C.white, 1.4);
    for (let i = 0; i < p.spaces; i++) {
      const cx = -w / 2 + i * stallLpx + stallLpx / 2;
      out += rect(cx - stallLpx * 0.3, bottom - 4, stallLpx * 0.6, 3.2, '#5a6b82');
    }
    out += aisleLabel(0, bottom + aisleWpx / 2, p.aisleW);
  }
  return out;
};
function aisleLabel(x, y, wm) {
  return `<text x="${r3(x)}" y="${r3(y)}" text-anchor="middle" font-size="11" fill="#7f93ab">通道 ${Number(wm).toFixed(1)} m</text>`;
}

/* ============================================================
 * 六、基础 SVG 工具
 * ============================================================ */
function line(x1, y1, x2, y2, stroke = C.white, sw = 1.5, dash) {
  return `<line x1="${r3(x1)}" y1="${r3(y1)}" x2="${r3(x2)}" y2="${r3(y2)}" stroke="${stroke}" stroke-width="${sw}"${dash ? ` stroke-dasharray="${dash}"` : ''}/>`;
}
function dashLine(x1, y1, x2, y2) { return line(x1, y1, x2, y2, C.white, 1.4, '10 9'); }
function rect(x, y, w, h, fill, stroke, sw) {
  return `<rect x="${r3(x)}" y="${r3(y)}" width="${r3(w)}" height="${r3(h)}" fill="${fill}"${stroke ? ` stroke="${stroke}" stroke-width="${sw || 1}"` : ''}/>`;
}
function circle(cx, cy, rr, fill, stroke, sw, dash) {
  return `<circle cx="${r3(cx)}" cy="${r3(cy)}" r="${r3(rr)}" fill="${fill}"${stroke ? ` stroke="${stroke}" stroke-width="${sw || 1.5}"${dash ? ` stroke-dasharray="${dash}"` : ''}` : ''}/>`;
}
function r3(v) { return Math.round(v * 1000) / 1000; }
function zebra(x, y, w, h, dir) {
  if (w <= 4 || h <= 4) return '';
  const step = 16, bar = 5; // PPM=12：间距约 1.35m、线宽约 0.4m，等宽短段不过密
  let out = '';
  if (dir === 'v') {
    const n = Math.max(2, Math.round(h / step)), sw = h / n;
    for (let i = 0; i < n; i++) out += rect(x, y + i * sw + (sw - bar) / 2, w, bar, C.white);
  } else {
    const n = Math.max(2, Math.round(w / step)), sw = w / n;
    for (let i = 0; i < n; i++) out += rect(x + i * sw + (sw - bar) / 2, y, bar, h, C.white);
  }
  return out;
}

/* ============================================================
 * 七、车辆渲染（车头朝 -y）
 * ============================================================ */
const WHEEL = '#10141a', GLASS = '#15222e';
function wheels(x, positions) {
  let out = '';
  positions.forEach(y => {
    out += rect(-x - 2.5, y - 4, 3.6, 8, WHEEL) + rect(x - 1.1, y - 4, 3.6, 8, WHEEL);
  });
  return out;
}
function headlights(y) { return rect(-8.5, y, 4.5, 2, '#fff3c0') + rect(4, y, 4.5, 2, '#fff3c0'); }

RENDER.sedan = el => {
  const col = el.props.color;
  return `<rect x="-11" y="-21" width="22" height="42" rx="7" fill="${col}" stroke="rgba(0,0,0,0.35)" stroke-width="1"/>
    <polygon points="-8,-14 8,-14 6.5,-5 -6.5,-5" fill="${GLASS}"/>
    <polygon points="-6.5,6 6.5,6 8,13 -8,13" fill="${GLASS}"/>
    ${wheels(10.5, [-12, 12])}${headlights(-20.5)}`;
};
RENDER.suv = el => {
  const col = el.props.color;
  return `<rect x="-12" y="-22" width="24" height="44" rx="6" fill="${col}" stroke="rgba(0,0,0,0.35)" stroke-width="1"/>
    ${rect(-9, -17, 18, 12, GLASS, 'rgba(255,255,255,0.12)', 0.8)}${rect(-9, 6, 18, 9, GLASS)}
    ${wheels(11.5, [-13, 13])}${headlights(-21.5)}`;
};
RENDER.truck = el => {
  const col = el.props.color;
  return rect(-13, -8, 26, 31, col, 'rgba(0,0,0,0.35)', 1) +
    rect(-12, -30, 24, 23, 5, col, 'rgba(0,0,0,0.35)', 1) +
    rect(-9, -27, 18, 9, GLASS) + line(-13, -8, 13, -8, 'rgba(0,0,0,0.4)', 1.5) +
    wheels(12.5, [-18, 14]) + headlights(-29.5);
};
RENDER.bus = el => {
  const col = el.props.color;
  let out = rect(-13, -32, 26, 64, 6, col, 'rgba(0,0,0,0.35)', 1);
  for (let i = 0; i < 5; i++) out += rect(-9.5, -27 + i * 10, 19, 6.5, GLASS);
  out += line(8, -30, 8, 28, 'rgba(0,0,0,0.3)', 1.2) + wheels(12.5, [-20, 20]) + headlights(-31.5);
  return out;
};
RENDER.two_wheeler = el => {
  const col = el.props.color;
  return circle(0, -14, 4.2, 'none', WHEEL, 2.4) + circle(0, 14, 4.2, 'none', WHEEL, 2.4) +
    `<path d="M0 -14 L-3 -2 L0 3 L0 14 M0 -2 L6 -8" stroke="${col}" stroke-width="2.6" fill="none" stroke-linecap="round"/>` +
    rect(-4.5, -4, 9, 3, '#222b38', 1.2) + line(6, -8, 8, -13, '#333', 2);
};

/* 行人（小人，面朝 -y，约 0.5 m 宽 × 1.7 m 高） */
RENDER.pedestrian = el => {
  const p = el.props, shirt = p.shirt || '#4a90d9';
  const walk = p.pose !== 'stand';
  const skin = '#e8b98a', pants = '#2f3a4a';
  let out = '';
  if (walk) {
    out += `<path d="M-1.4 2 L-4.4 9.4" stroke="${pants}" stroke-width="2.4" stroke-linecap="round"/>`;
    out += `<path d="M1.4 2 L4.4 9.4" stroke="${pants}" stroke-width="2.4" stroke-linecap="round"/>`;
    out += `<path d="M-2.6 -4 L-5 1.2" stroke="${shirt}" stroke-width="2.2" stroke-linecap="round"/>`;
    out += `<path d="M2.6 -4 L5 1.2" stroke="${shirt}" stroke-width="2.2" stroke-linecap="round"/>`;
  } else {
    out += line(-1.4, 2, -1.4, 9.4, pants, 2.4);
    out += line(1.4, 2, 1.4, 9.4, pants, 2.4);
    out += line(-2.8, -4, -3.4, 1.4, shirt, 2.2);
    out += line(2.8, -4, 3.4, 1.4, shirt, 2.2);
  }
  out += rect(-3.2, -5, 6.4, 7.5, 1.6, shirt, 'rgba(0,0,0,0.25)', 0.8);
  out += circle(0, -8.2, 3, skin, 'rgba(0,0,0,0.3)', 0.8);
  return out;
};

/* ============================================================
 * 八、GB 5768 交通标志
 * ============================================================ */
const TRI = 'M0 -19 L-18.5 13.5 L18.5 13.5 Z';
function warnTriangle(inner) {
  return `<path d="${TRI}" fill="${C.signYellow}" stroke="${C.black}" stroke-width="2.4" stroke-linejoin="round"/>${inner}`;
}
RENDER.warn_danger = () => warnTriangle(rect(-1.6, -11, 3.2, 11, C.black, 2.5) + circle(0, 7, 2, C.black));
RENDER.warn_pedestrian = () => warnTriangle(
  circle(0, -8, 2.6, C.black) +
  `<path d="M0 -5 L-3 2 L-5 8 M0 -5 L3 2 L5 7 M-2 -1 L2 -1" stroke="${C.black}" stroke-width="2" fill="none" stroke-linecap="round"/>`);
RENDER.warn_children = () => warnTriangle(
  circle(-5, -6, 2.2, C.black) + `<path d="M-5 -3.5 L-7 8 M-3 -1 L-8 1" stroke="${C.black}" stroke-width="1.7" fill="none" stroke-linecap="round"/>` +
  circle(5, -6, 2.2, C.black) + `<path d="M5 -3.5 L3 8 M7 -1 L2 1" stroke="${C.black}" stroke-width="1.7" fill="none" stroke-linecap="round"/>`);
RENDER.warn_signal = () => warnTriangle(
  rect(-4, -11, 8, 19, 2, C.black) +
  circle(0, -7, 1.7, C.lampRed) + circle(0, -1.5, 1.7, C.lampYellow) + circle(0, 4, 1.7, C.lampGreen));
RENDER.warn_cross = () => warnTriangle(rect(-2.2, -11, 4.4, 22, C.black) + rect(-11, -2.2, 22, 4.4, C.black));
RENDER.warn_bend_l = () => warnTriangle(
  `<path d="M7 9 L7 -2 A8 8 0 00-7 -9" stroke="${C.black}" stroke-width="2.6" fill="none" stroke-linecap="round"/>
   <path d="M-7 -9 L-2.5 -9.5 L-5 -4.5 Z" fill="${C.black}"/>`);
RENDER.warn_bend_r = () => warnTriangle(
  `<path d="M-7 9 L-7 -2 A8 8 0 017 -9" stroke="${C.black}" stroke-width="2.6" fill="none" stroke-linecap="round"/>
   <path d="M7 -9 L2.5 -9.5 L5 -4.5 Z" fill="${C.black}"/>`);
RENDER.warn_slow = () => warnTriangle(
  `<text x="0" y="2" text-anchor="middle" font-size="15" font-weight="700" fill="${C.black}">慢</text>`);
RENDER.warn_work = () => warnTriangle(
  circle(-3, -8, 2.4, C.black) +
  `<path d="M-3 -5 L-6 8 M0 -2 L-7 2 M4 -10 L9 9" stroke="${C.black}" stroke-width="2" fill="none" stroke-linecap="round"/>`);

function banCircle(inner, fullRed) {
  return circle(0, 0, 19, fullRed ? C.signRed : '#fff', C.signRed, 3.4) + inner;
}
const SLASH = line(-12, 12, 12, -12, C.signRed, 3.2);
RENDER.ban_no_entry = () => banCircle(rect(-11, -3.2, 22, 6.4, 2, C.white), true);
RENDER.ban_no_motor = () => banCircle(
  rect(-6, -8, 12, 14, 3, C.black) + rect(-4.5, -6, 9, 5, GLASS) + SLASH);
RENDER.ban_speed = el => banCircle(
  `<text x="0" y="1" text-anchor="middle" font-size="13" font-weight="700" fill="${C.black}">${el.props.limit}</text>`);
RENDER.ban_no_park = () => circle(0, 0, 19, C.signBlue, C.signRed, 3.2) +
  line(-10, -10, 10, 10, C.signRed, 3) + line(10, -10, -10, 10, C.signRed, 3);
RENDER.ban_no_horn = () => banCircle(
  `<path d="M-8 -3 L-2 -3 L7 -9 L7 9 L-2 3 L-8 3 Z" fill="${C.black}"/>` + SLASH);
RENDER.ban_no_uturn = () => banCircle(
  `<path d="M-7 9 V-3 A7 7 0 017 4 V9" stroke="${C.black}" stroke-width="2.6" fill="none" stroke-linecap="round"/>
   <path d="M7 9 L3 4.5 L11 4.5 Z" fill="${C.black}"/>` + SLASH);
RENDER.ban_stop = () => {
  const pts = [];
  for (let i = 0; i < 8; i++) {
    const a = -Math.PI / 8 + i * Math.PI / 4;
    pts.push(`${r3(21 * Math.sin(a))},${r3(-21 * Math.cos(a))}`);
  }
  return `<polygon points="${pts.join(' ')}" fill="${C.signRed}" stroke="#fff" stroke-width="1.6"/>
    <text x="0" y="1" text-anchor="middle" font-size="15" font-weight="700" fill="#fff">停</text>`;
};
RENDER.ban_give_way = () =>
  `<path d="M0 19 L-18.5 -12 L18.5 -12 Z" fill="#fff" stroke="${C.signRed}" stroke-width="3" stroke-linejoin="round"/>
   <text x="0" y="2" text-anchor="middle" font-size="14" font-weight="700" fill="${C.signRed}">让</text>`;

function arrowUp() { return `<path d="M0 -12 L-6 -4 L-2.5 -4 L-2.5 10 L2.5 10 L2.5 -4 L6 -4 Z" fill="#fff"/>`; }
function bendArrow(side) {
  const d = side === 'l' ? `M6 11 V-1 A7 7 0 00-6 -8` : `M-6 11 V-1 A7 7 0 016 -8`;
  return `<path d="${d}" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>
    <path d="${side === 'l' ? 'M-6 -8 L-2 -8.5 L-4 -4 Z' : 'M6 -8 L2 -8.5 L4 -4 Z'}" fill="#fff"/>`;
}
RENDER.ind_straight = () => circle(0, 0, 19, C.signBlue) + arrowUp();
RENDER.ind_turn_l = () => circle(0, 0, 19, C.signBlue) + bendArrow('l');
RENDER.ind_turn_r = () => circle(0, 0, 19, C.signBlue) + bendArrow('r');
RENDER.ind_motor = () => circle(0, 0, 19, C.signBlue) +
  rect(-6, -9, 12, 15, 3, '#fff') + rect(-4.5, -7, 9, 5, C.signBlue);
RENDER.ind_crosswalk = () => rect(-18, -18, 36, 36, 4, C.signBlue) +
  circle(0, -8, 2.4, '#fff') + `<path d="M0 -5 L-3 3 M0 -5 L3 3" stroke="#fff" stroke-width="2" stroke-linecap="round"/>` +
  zebra(-13, 7, 26, 7, 'h');
RENDER.ind_parking = () => rect(-18, -18, 36, 36, 4, C.signBlue) +
  `<text x="0" y="2" text-anchor="middle" font-size="20" font-weight="700" fill="#fff">P</text>`;

/* ============================================================
 * 九、障碍物
 * ============================================================ */
RENDER.cone = () =>
  rect(-11, 8, 22, 4, 1.5, '#1a1f27') +
  `<path d="M-8 8 L-2.5 -12 L2.5 -12 L8 8 Z" fill="${C.orange}" stroke="rgba(0,0,0,0.3)" stroke-width="0.8"/>` +
  rect(-5.5, -5, 11, 3, '#f4f7fb') + rect(-7, 2.5, 14, 3, '#f4f7fb');
RENDER.water_barrier = () =>
  `<path d="M-20 10 Q-21 -8 -15 -11 L15 -11 Q21 -8 20 10 Z" fill="${C.signRed}" stroke="rgba(0,0,0,0.3)" stroke-width="1"/>` +
  rect(-19, -2, 38, 6, '#f4f7fb') + circle(-8, -8, 2.4, '#7a1f24') + circle(8, -8, 2.4, '#7a1f24');
RENDER.crash_barrel = () =>
  ellipse(0, -13, 12, 4.5, '#3a4555') + rect(-12, -13, 24, 27, '#e8edf3') +
  rect(-12, -8, 24, 5, C.signRed) + rect(-12, 3, 24, 5, C.signRed) + ellipse(0, -13, 7, 2.6, '#222b38');
RENDER.guardrail = () => {
  let beam = `<path d="M-46 -6`;
  for (let x = -46; x < 46; x += 8) beam += ` q4 6 8 0`;
  beam += `" fill="none" stroke="#9fb4cc" stroke-width="3.4" stroke-linecap="round"/>`;
  return beam + rect(-44, -3, 5, 13, '#5a6b82') + rect(39, -3, 5, 13, '#5a6b82');
};
RENDER.fence = () => {
  let out = rect(-46, -14, 92, 24, 2, '#2f6fb5');
  for (let x = -46; x < 46; x += 12) out += `<path d="M${x} 10 L${x + 12} -14" stroke="#e8f1fb" stroke-width="4"/>`;
  out += rect(-46, 8, 92, 3, C.yellow) + rect(-44, 10, 5, 6, '#3a4a5f') + rect(39, 10, 5, 6, '#3a6b82');
  return out;
};
RENDER.beacon = () =>
  rect(-8, 6, 16, 6, 2, '#2a3442') + circle(0, -2, 7, 'rgba(245,197,66,0.25)') +
  circle(0, -2, 4.6, C.yellow) + line(0, -9, 0, -13, '#3a4a5f', 2);
RENDER.free_obstacle = el => {
  const w = el.w || 120, h = el.h || 120, x = -w / 2, y = -h / 2;
  const color = el.props.color || '#d9343b';
  let out = rect(x, y, w, h, hexA(color, 0.16), color, 2);
  // 内部斜线阴影，提示不可通行区域
  for (let d = -h; d < w; d += 24) {
    out += `<path d="M${r3(x + Math.max(0, d))} ${r3(y + Math.max(0, -d))} L${r3(x + Math.min(w, d + h))} ${r3(y + Math.min(h, h - d))}" stroke="${hexA(color, 0.35)}" stroke-width="1"/>`;
  }
  const label = el.props.label || '';
  const wm = el.props.width_m != null ? el.props.width_m : (el.props.sizeW != null ? el.props.sizeW : (w / PPM).toFixed(2));
  const dm = el.props.depth_m != null ? el.props.depth_m : (el.props.sizeH != null ? el.props.sizeH : (h / PPM).toFixed(2));
  out += rect(-Math.min(120, w / 2) , -9, Math.min(240, w), 18, 'rgba(12,18,26,0.75)');
  out += `<text x="0" y="4" text-anchor="middle" font-size="12" fill="${C.white}">${esc(label ? label + ' · ' : '')}${wm} × ${dm} m</text>`;
  return out;
};
function hexA(hex, alpha) {
  const h = String(hex).replace('#', '');
  const r = parseInt(h.substring(0, 2), 16), g = parseInt(h.substring(2, 4), 16), b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
function esc(s) { return String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])); }
function ellipse(cx, cy, rx, ry, fill) {
  return `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}"/>`;
}

/* ============================================================
 * 十、交通信号灯（GB 14887）
 * ============================================================ */
function glow(cx, cy, color, rr = 6.4, alpha = 0.28) {
  const h = color.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16), g = parseInt(h.substring(2, 4), 16), b = parseInt(h.substring(4, 6), 16);
  return circle(cx, cy, rr, `rgba(${r},${g},${b},${alpha})`);
}
function lamp(cx, cy, color, on) {
  return on ? glow(cx, cy, color) + circle(cx, cy, 4.2, color) : circle(cx, cy, 4.2, '#333d4c');
}
function vehicleLamp(el, arrow) {
  const a = el.props.active;
  let out = rect(-11, -34, 22, 68, 6, C.housing, 'rgba(120,170,230,0.3)', 1.2);
  const ys = [-22, 0, 22], cols = [C.lampRed, C.lampYellow, C.lampGreen], keys = ['red', 'yellow', 'green'];
  ys.forEach((y, i) => {
    if (arrow) out += a === keys[i] ? arrowLamp(0, y, cols[i]) : circle(0, y, 4.2, '#333d4c');
    else out += lamp(0, y, cols[i], a === keys[i]);
  });
  return out;
}
function arrowLamp(cx, cy, color) {
  return glow(cx, cy, color, 6.4, 0.3) +
    `<path d="M${cx} ${cy - 5} L${cx - 3.4} ${cy - 0.5} L${cx - 1.5} ${cy - 0.5} L${cx - 1.5} ${cy + 4.5} L${cx + 1.5} ${cy + 4.5} L${cx + 1.5} ${cy - 0.5} L${cx + 3.4} ${cy - 0.5} Z" fill="${color}"/>`;
}
RENDER.light_vehicle = el => vehicleLamp(el, false);
RENDER.light_arrow = el => vehicleLamp(el, true);
RENDER.light_flash = () =>
  rect(-10, -11, 20, 22, 5, C.housing) + circle(0, 0, 7.5, 'rgba(255,197,49,0.3)') + circle(0, 0, 5, C.lampYellow);
RENDER.light_lane = el => {
  const a = el.props.active;
  let out = rect(-31, -12, 62, 24, 5, C.housing, 'rgba(120,170,230,0.3)', 1.2);
  if (a === 'red') {
    out += glow(-16, 0, C.lampRed) + line(-19.5, -3.5, -12.5, 3.5, C.lampRed, 2.6) + line(-12.5, -3.5, -19.5, 3.5, C.lampRed, 2.6);
  } else out += circle(-16, 0, 4.2, '#333d4c');
  if (a === 'green') {
    out += glow(16, 0, C.lampGreen) +
      `<path d="M16 -5 L12.6 -0.5 L14.5 -0.5 L14.5 4 L17.5 4 L17.5 -0.5 L19.4 -0.5 Z" fill="${C.lampGreen}"/>`;
  } else out += circle(16, 0, 4.2, '#333d4c');
  return out;
};
