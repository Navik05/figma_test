/**
 * Vector Illustration Assembler - Main Application Logic
 * Interactive SVG canvas, layer management, automated generation (Scenarios 1 & 2),
 * live palette recoloring, and vector export.
 */

// Application State
const state = {
  canvasWidth: 1000,
  canvasHeight: 1000,
  activeSize: 'L',
  activePaletteId: 'palette_1',
  backgroundType: 'pattern',
  library: [],
  palettes: [],
  canvasItems: [],
  selectedItemId: null,
  scenario2Selected: new Set(['книга', 'лампа', 'монета']),
  history: [],
  historyIndex: -1,
  drag: null,
};

// DOM Elements
const elements = {};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  elements.canvasContainer = document.getElementById('canvas_container');
  elements.svgRoot = document.getElementById('composition_svg_root');
  elements.selectionBox = document.getElementById('selection_box');
  elements.libContainer = document.getElementById('library_items_container');
  elements.palettesContainer = document.getElementById('palettes_container');
  elements.scenario2Chips = document.getElementById('scenario2_chips_container');
  elements.reasoningBox = document.getElementById('metaphor_reasoning_box');
  elements.reasoningText = document.getElementById('metaphor_reasoning_text');
  elements.toastContainer = document.getElementById('toast_container');

  initApp();
  initCanvasInteractions();
});

async function initApp() {
  await Promise.all([loadLibrary(), loadPalettes()]);
  renderScenario2Chips();

  // Run initial automated composition to showcase capability
  await runMetaphorComposition('Финансовая подушка и рост сбережений');
}

// --------------------------------------------------------------------------
// API Calls & Data Loading
// --------------------------------------------------------------------------

async function loadLibrary() {
  try {
    const res = await fetch(`/api/library?size=${state.activeSize}`);
    const data = await res.json();
    state.library = data.components || [];
    renderLibrary();
    document.getElementById('lib_count_badge').textContent = `${state.library.length} элементов`;
  } catch (err) {
    console.error('Failed to load library:', err);
    showToast('Ошибка загрузки библиотеки', 'error');
  }
}

async function loadPalettes() {
  try {
    const res = await fetch('/api/palettes');
    const data = await res.json();
    state.palettes = data.palettes || [];
    renderPalettes();
  } catch (err) {
    console.error('Failed to load palettes:', err);
  }
}

// --------------------------------------------------------------------------
// Rendering UI Components
// --------------------------------------------------------------------------

function renderLibrary(filtered = null) {
  const items = filtered !== null ? filtered : state.library;
  elements.libContainer.innerHTML = '';

  items.forEach((comp) => {
    const card = document.createElement('div');
    card.className = 'library-card';
    card.onclick = () => addComponentToCanvas(comp.name);

    const hasS = comp.has_size_s;
    const badgeHtml = state.activeSize === 'S'
      ? `<span class="library-badge-s">${hasS ? 'Размер S' : 'L (S ожидается)'}</span>`
      : `<span class="library-badge-s">Размер L</span>`;

    card.innerHTML = `
      ${badgeHtml}
      <div class="library-thumb-wrap" id="thumb_${comp.name}">
        <span style="font-size:11px; color:var(--text-dim)">Загрузка...</span>
      </div>
      <div class="library-card-name">${comp.name}</div>
    `;

    elements.libContainer.appendChild(card);

    // Load preview SVG
    fetch(`/api/component/svg?name=${encodeURIComponent(comp.name)}&size=${state.activeSize}&palette=${state.activePaletteId}`)
      .then((r) => (r.ok ? r.text() : ''))
      .then((svgText) => {
        const thumb = document.getElementById(`thumb_${comp.name}`);
        if (thumb && svgText) {
          thumb.innerHTML = svgText;
        }
      })
      .catch(() => {});
  });
}

function filterLibrary() {
  const query = document.getElementById('lib_search_input').value.toLowerCase().trim();
  if (!query) {
    renderLibrary();
    return;
  }
  const filtered = state.library.filter((comp) => {
    if (comp.name.toLowerCase().includes(query)) return true;
    return comp.tags && comp.tags.some((t) => t.toLowerCase().includes(query));
  });
  renderLibrary(filtered);
}

function renderPalettes() {
  elements.palettesContainer.innerHTML = '';

  state.palettes.forEach((pal) => {
    const card = document.createElement('div');
    card.className = `palette-card ${pal.id === state.activePaletteId ? 'active' : ''}`;
    card.onclick = () => selectPalette(pal.id);

    const swatchesHtml = pal.colors
      .map((c) => `<div class="palette-swatch-slot" style="background-color: ${c}" title="${c}"></div>`)
      .join('');

    card.innerHTML = `
      <div class="palette-name">
        <span>${pal.name}</span>
        ${pal.id === state.activePaletteId ? '<span style="color:var(--accent-primary)">✓ Активна</span>' : ''}
      </div>
      <div class="palette-swatches">
        ${swatchesHtml}
      </div>
    `;

    elements.palettesContainer.appendChild(card);
  });
}

function renderScenario2Chips() {
  elements.scenario2Chips.innerHTML = '';
  state.library.forEach((comp) => {
    const chip = document.createElement('span');
    const isSelected = state.scenario2Selected.has(comp.name);
    chip.className = `chip ${isSelected ? 'selected' : ''}`;
    chip.textContent = `${isSelected ? '✓ ' : '+ '}${comp.name}`;
    chip.onclick = () => {
      if (state.scenario2Selected.has(comp.name)) {
        state.scenario2Selected.delete(comp.name);
      } else {
        state.scenario2Selected.add(comp.name);
      }
      renderScenario2Chips();
    };
    elements.scenario2Chips.appendChild(chip);
  });
}

// --------------------------------------------------------------------------
// Canvas Rendering & SVG Export
// --------------------------------------------------------------------------

async function renderCanvas() {
  try {
    const res = await fetch('/api/export/svg', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        canvas_width: state.canvasWidth,
        canvas_height: state.canvasHeight,
        items: state.canvasItems,
        palette_id: state.activePaletteId,
        background_type: state.backgroundType,
        size: state.activeSize,
      }),
    });

    const data = await res.json();
    if (data.svg) {
      elements.svgRoot.innerHTML = '';

      // Parse inner svg
      const parser = new DOMParser();
      const doc = parser.parseFromString(data.svg, 'image/svg+xml');
      const docRoot = doc.documentElement;

      // Copy inner children and attributes
      elements.svgRoot.setAttribute('viewBox', `0 0 ${state.canvasWidth} ${state.canvasHeight}`);
      Array.from(docRoot.childNodes).forEach((node) => {
        elements.svgRoot.appendChild(document.importNode(node, true));
      });

      attachElementClickHandlers();
      updateSelectionBox();
    }
  } catch (err) {
    console.error('Error rendering canvas:', err);
  }
}

function attachElementClickHandlers() {
  state.canvasItems.forEach((item) => {
    const el = document.getElementById(item.id);
    if (el) {
      el.style.cursor = 'move';
      el.onmousedown = (e) => {
        e.stopPropagation();
        selectItem(item.id);
        startDragging(e, item.id);
      };
    }
  });
}

// --------------------------------------------------------------------------
// Element Selection & Interactive Manipulation
// --------------------------------------------------------------------------

function selectItem(itemId) {
  state.selectedItemId = itemId;
  const item = state.canvasItems.find((it) => it.id === itemId);

  if (!item) {
    elements.selectionBox.style.display = 'none';
    document.getElementById('inspector_empty_notice').style.display = 'block';
    document.getElementById('inspector_controls').style.display = 'none';
    return;
  }

  // Update selection box
  elements.selectionBox.style.display = 'block';
  updateSelectionBox();

  // Update Inspector Tab
  document.getElementById('inspector_empty_notice').style.display = 'none';
  document.getElementById('inspector_controls').style.display = 'flex';
  document.getElementById('inspector_item_name').textContent = item.name.toUpperCase();
  
  const badge = document.getElementById('inspector_item_badge');
  badge.textContent = item.is_background ? 'Фоновый' : 'Главный';
  badge.style.backgroundColor = item.is_background ? 'rgba(120, 100, 215, 0.2)' : 'rgba(16, 185, 129, 0.2)';
  badge.style.color = item.is_background ? '#baaef0' : '#6ee7b7';

  document.getElementById('inspector_role_toggle').textContent = item.is_background
    ? '🎨 Сделать Главным'
    : '🎨 Сделать Фоновым';

  document.getElementById('quickbar_role_text').textContent = item.is_background
    ? 'Главный'
    : 'Фоновый';

  document.getElementById('inspector_x').value = Math.round(item.x);
  document.getElementById('inspector_y').value = Math.round(item.y);
  document.getElementById('inspector_scale').value = item.scale.toFixed(2);
  document.getElementById('inspector_scale_range').value = item.scale;
  document.getElementById('inspector_rot').value = Math.round(item.rotation || 0);
  document.getElementById('inspector_rot_range').value = Math.round(item.rotation || 0);
}

function updateSelectionBox() {
  if (!state.selectedItemId) {
    elements.selectionBox.style.display = 'none';
    return;
  }

  const item = state.canvasItems.find((it) => it.id === state.selectedItemId);
  if (!item) {
    elements.selectionBox.style.display = 'none';
    return;
  }

  // Calculate container scale ratio
  const rect = elements.canvasContainer.getBoundingClientRect();
  const scaleX = rect.width / state.canvasWidth;
  const scaleY = rect.height / state.canvasHeight;

  const widthOnCanvas = item.natural_width * item.scale * scaleX;
  const heightOnCanvas = item.natural_height * item.scale * scaleY;
  const xOnCanvas = item.x * scaleX;
  const yOnCanvas = item.y * scaleY;

  elements.selectionBox.style.width = `${widthOnCanvas}px`;
  elements.selectionBox.style.height = `${heightOnCanvas}px`;
  elements.selectionBox.style.left = `${xOnCanvas}px`;
  elements.selectionBox.style.top = `${yOnCanvas}px`;
  elements.selectionBox.style.transform = `rotate(${item.rotation || 0}deg)`;
  elements.selectionBox.style.display = 'block';
}

function updateItemProp(prop, val) {
  if (!state.selectedItemId) return;
  const item = state.canvasItems.find((it) => it.id === state.selectedItemId);
  if (!item) return;

  const num = parseFloat(val);
  if (isNaN(num)) return;

  if (prop === 'scale') {
    // Strictly preserve uniform aspect ratio
    item.scale = Math.max(0.05, Math.min(3.0, num));
  } else if (prop === 'rotation') {
    item.rotation = num;
  } else if (prop === 'x') {
    item.x = num;
  } else if (prop === 'y') {
    item.y = num;
  }

  selectItem(state.selectedItemId);
  renderCanvas();
}

function toggleSelectedItemRole() {
  if (!state.selectedItemId) return;
  const item = state.canvasItems.find((it) => it.id === state.selectedItemId);
  if (!item) return;

  item.is_background = !item.is_background;
  showToast(`Объект «${item.name}» переключен в режим: ${item.is_background ? 'Фоновый' : 'Главный'}`);
  selectItem(state.selectedItemId);
  renderCanvas();
}

function rotateSelectedItem(deg) {
  if (!state.selectedItemId) return;
  const item = state.canvasItems.find((it) => it.id === state.selectedItemId);
  if (!item) return;

  item.rotation = ((item.rotation || 0) + deg) % 360;
  selectItem(state.selectedItemId);
  renderCanvas();
}

function moveSelectedItemLayer(delta) {
  if (!state.selectedItemId) return;
  const idx = state.canvasItems.findIndex((it) => it.id === state.selectedItemId);
  if (idx === -1) return;

  const item = state.canvasItems[idx];
  state.canvasItems.splice(idx, 1);

  if (delta === 999) {
    state.canvasItems.push(item);
  } else if (delta === -999) {
    state.canvasItems.unshift(item);
  } else {
    const newIdx = Math.max(0, Math.min(state.canvasItems.length, idx + delta));
    state.canvasItems.splice(newIdx, 0, item);
  }

  // Re-index z_index
  state.canvasItems.forEach((it, i) => (it.z_index = i));
  selectItem(state.selectedItemId);
  renderCanvas();
}

function duplicateSelectedItem() {
  if (!state.selectedItemId) return;
  const item = state.canvasItems.find((it) => it.id === state.selectedItemId);
  if (!item) return;

  const newItem = {
    ...item,
    id: `elem_${Date.now()}_${item.name}`,
    x: item.x + 30,
    y: item.y + 30,
    z_index: state.canvasItems.length,
  };

  state.canvasItems.push(newItem);
  selectItem(newItem.id);
  renderCanvas();
  showToast(`Создан дубликат «${item.name}»`);
}

function deleteSelectedItem() {
  if (!state.selectedItemId) return;
  const idx = state.canvasItems.findIndex((it) => it.id === state.selectedItemId);
  if (idx !== -1) {
    const name = state.canvasItems[idx].name;
    state.canvasItems.splice(idx, 1);
    selectItem(null);
    renderCanvas();
    showToast(`Удален объект «${name}»`);
  }
}

function addComponentToCanvas(name) {
  const meta = state.library.find((c) => c.name === name);
  const natW = meta ? meta.width : 500;
  const natH = meta ? meta.height : 500;

  // Base scale calculation so proportions are preserved
  const baseScale = (Math.min(state.canvasWidth, state.canvasHeight) / 1000.0) * 0.45;

  const newItem = {
    id: `elem_${Date.now()}_${name}`,
    name: name,
    is_background: false,
    x: (state.canvasWidth - natW * baseScale) / 2 + (Math.random() * 40 - 20),
    y: (state.canvasHeight - natH * baseScale) / 2 + (Math.random() * 40 - 20),
    scale: parseFloat(baseScale.toFixed(3)),
    rotation: Math.round(Math.random() * 12 - 6),
    natural_width: natW,
    natural_height: natH,
    viewBox: meta ? meta.viewBox : `0 0 ${natW} ${natH}`,
    z_index: state.canvasItems.length,
  };

  state.canvasItems.push(newItem);
  selectItem(newItem.id);
  renderCanvas();
  showToast(`Добавлен объект «${name}» на холст`);
}

function clearCanvas() {
  if (state.canvasItems.length === 0) return;
  state.canvasItems = [];
  selectItem(null);
  renderCanvas();
  showToast('Холст очищен');
}

// --------------------------------------------------------------------------
// Mouse & Dragging Interactions
// --------------------------------------------------------------------------

function initCanvasInteractions() {
  const handleResize = document.getElementById('handle_resize');
  const handleRotate = document.getElementById('handle_rotate');

  handleResize.addEventListener('mousedown', (e) => {
    e.stopPropagation();
    startHandleAction(e, 'resize');
  });

  handleRotate.addEventListener('mousedown', (e) => {
    e.stopPropagation();
    startHandleAction(e, 'rotate');
  });

  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);

  // Keyboard shortcuts
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    if (e.key === 'Delete' || e.key === 'Backspace') {
      deleteSelectedItem();
    } else if (e.key === 'd' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      duplicateSelectedItem();
    } else if (e.key === 'ArrowLeft') {
      updateItemProp('x', (state.canvasItems.find((it) => it.id === state.selectedItemId)?.x || 0) - 5);
    } else if (e.key === 'ArrowRight') {
      updateItemProp('x', (state.canvasItems.find((it) => it.id === state.selectedItemId)?.x || 0) + 5);
    } else if (e.key === 'ArrowUp') {
      updateItemProp('y', (state.canvasItems.find((it) => it.id === state.selectedItemId)?.y || 0) - 5);
    } else if (e.key === 'ArrowDown') {
      updateItemProp('y', (state.canvasItems.find((it) => it.id === state.selectedItemId)?.y || 0) + 5);
    }
  });
}

function startDragging(e, itemId) {
  const item = state.canvasItems.find((it) => it.id === itemId);
  if (!item) return;

  const rect = elements.canvasContainer.getBoundingClientRect();
  const scale = rect.width / state.canvasWidth;

  state.drag = {
    type: 'move',
    itemId: itemId,
    startX: e.clientX,
    startY: e.clientY,
    origItemX: item.x,
    origItemY: item.y,
    scaleFactor: scale,
  };
}

function startHandleAction(e, actionType) {
  const item = state.canvasItems.find((it) => it.id === state.selectedItemId);
  if (!item) return;

  const rect = elements.canvasContainer.getBoundingClientRect();
  const scale = rect.width / state.canvasWidth;

  state.drag = {
    type: actionType,
    itemId: item.id,
    startX: e.clientX,
    startY: e.clientY,
    origScale: item.scale,
    origRot: item.rotation || 0,
    centerX: rect.left + (item.x + (item.natural_width * item.scale) / 2) * scale,
    centerY: rect.top + (item.y + (item.natural_height * item.scale) / 2) * scale,
  };
}

function onMouseMove(e) {
  if (!state.drag) return;

  const item = state.canvasItems.find((it) => it.id === state.drag.itemId);
  if (!item) return;

  if (state.drag.type === 'move') {
    const dx = (e.clientX - state.drag.startX) / state.drag.scaleFactor;
    const dy = (e.clientY - state.drag.startY) / state.drag.scaleFactor;
    item.x = Math.round(state.drag.origItemX + dx);
    item.y = Math.round(state.drag.origItemY + dy);
    updateSelectionBox();
    document.getElementById('inspector_x').value = item.x;
    document.getElementById('inspector_y').value = item.y;

    const el = document.getElementById(item.id);
    if (el) {
      const cx = (item.natural_width / 2) * item.scale;
      const cy = (item.natural_height / 2) * item.scale;
      el.setAttribute(
        'transform',
        `translate(${item.x}, ${item.y}) rotate(${item.rotation || 0}, ${cx}, ${cy}) scale(${item.scale})`
      );
    }
  } else if (state.drag.type === 'resize') {
    // Uniform scale preserving aspect ratio
    const dy = (e.clientY - state.drag.startY) / 150.0;
    const dx = (e.clientX - state.drag.startX) / 150.0;
    const delta = Math.max(dx, dy);
    const newScale = Math.max(0.1, Math.min(2.5, state.drag.origScale + delta));
    item.scale = parseFloat(newScale.toFixed(3));
    updateSelectionBox();
    document.getElementById('inspector_scale').value = item.scale.toFixed(2);
    document.getElementById('inspector_scale_range').value = item.scale;

    const el = document.getElementById(item.id);
    if (el) {
      const cx = (item.natural_width / 2) * item.scale;
      const cy = (item.natural_height / 2) * item.scale;
      el.setAttribute(
        'transform',
        `translate(${item.x}, ${item.y}) rotate(${item.rotation || 0}, ${cx}, ${cy}) scale(${item.scale})`
      );
    }
  } else if (state.drag.type === 'rotate') {
    const angle = Math.atan2(e.clientY - state.drag.centerY, e.clientX - state.drag.centerX);
    const deg = Math.round(angle * (180 / Math.PI) + 90);
    item.rotation = deg;
    updateSelectionBox();
    document.getElementById('inspector_rot').value = deg;
    document.getElementById('inspector_rot_range').value = deg;

    const el = document.getElementById(item.id);
    if (el) {
      const cx = (item.natural_width / 2) * item.scale;
      const cy = (item.natural_height / 2) * item.scale;
      el.setAttribute(
        'transform',
        `translate(${item.x}, ${item.y}) rotate(${item.rotation || 0}, ${cx}, ${cy}) scale(${item.scale})`
      );
    }
  }
}

function onMouseUp() {
  if (state.drag) {
    state.drag = null;
    renderCanvas();
  }
}

function onViewportClick(e) {
  if (e.target === elements.canvasContainer || e.target.id === 'canvas_viewport') {
    selectItem(null);
  }
}

// --------------------------------------------------------------------------
// Automated Scenarios (Scenario 1 & 2)
// --------------------------------------------------------------------------

function setMetaphorPrompt(text) {
  document.getElementById('metaphor_input').value = text;
  runMetaphorComposition(text);
}

async function runMetaphorComposition(customPrompt = null) {
  const prompt = customPrompt || document.getElementById('metaphor_input').value || 'Идеи и творчество';
  const preset = document.getElementById('metaphor_preset_select').value;

  try {
    const res = await fetch('/api/compose/metaphor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt,
        canvas_width: state.canvasWidth,
        canvas_height: state.canvasHeight,
        size: state.activeSize,
        palette_id: state.activePaletteId,
        background_type: state.backgroundType,
        preset: preset === 'auto' ? null : preset,
      }),
    });

    const data = await res.json();
    if (data.items) {
      state.canvasItems = data.items;
      elements.reasoningBox.style.display = 'block';
      elements.reasoningText.textContent = data.reasoning;
      selectItem(data.items[0]?.id || null);
      renderCanvas();
      showToast('Композиция успешно собрана по метафоре!');
    }
  } catch (err) {
    console.error('Error running metaphor composition:', err);
    showToast('Ошибка сборки по метафоре', 'error');
  }
}

async function runComponentsComposition() {
  const components = Array.from(state.scenario2Selected);
  if (components.length === 0) {
    showToast('Выберите хотя бы один компонент', 'error');
    return;
  }

  const preset = document.getElementById('components_preset_select').value;

  try {
    const res = await fetch('/api/compose/components', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        components: components,
        canvas_width: state.canvasWidth,
        canvas_height: state.canvasHeight,
        size: state.activeSize,
        palette_id: state.activePaletteId,
        background_type: state.backgroundType,
        preset: preset === 'auto' ? null : preset,
      }),
    });

    const data = await res.json();
    if (data.items) {
      state.canvasItems = data.items;
      selectItem(data.items[0]?.id || null);
      renderCanvas();
      showToast(`Скомпоновано ${components.length} компонентов!`);
    }
  } catch (err) {
    console.error('Error in components composition:', err);
    showToast('Ошибка сборки сцены', 'error');
  }
}

async function shuffleComposition() {
  const seed = Math.floor(Math.random() * 100000);
  const components = state.canvasItems.map((it) => ({
    name: it.name,
    is_background: it.is_background,
  }));

  if (components.length === 0) {
    runMetaphorComposition();
    return;
  }

  try {
    const res = await fetch('/api/compose/components', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        components: components,
        canvas_width: state.canvasWidth,
        canvas_height: state.canvasHeight,
        size: state.activeSize,
        palette_id: state.activePaletteId,
        background_type: state.backgroundType,
        seed: seed,
      }),
    });

    const data = await res.json();
    if (data.items) {
      state.canvasItems = data.items;
      selectItem(data.items[0]?.id || null);
      renderCanvas();
      showToast('Расстановка объектов перемешана!');
    }
  } catch (err) {
    console.error('Error shuffling:', err);
  }
}

// --------------------------------------------------------------------------
// Palette Management & Automatic Recoloring
// --------------------------------------------------------------------------

function selectPalette(paletteId) {
  state.activePaletteId = paletteId;
  renderPalettes();
  renderLibrary();
  renderCanvas();
  showToast(`Применена палитра: ${state.palettes.find((p) => p.id === paletteId)?.name || paletteId}`);
}

// --------------------------------------------------------------------------
// Controls: Size, Format, Background
// --------------------------------------------------------------------------

function setSizeMode(size) {
  state.activeSize = size;
  document.getElementById('btn_size_l').classList.toggle('active', size === 'L');
  document.getElementById('btn_size_s').classList.toggle('active', size === 'S');

  loadLibrary();
  renderCanvas();
  showToast(`Активен размер иллюстраций: ${size}`);
}

function onFormatChange(val) {
  if (val === 'custom') {
    const w = prompt('Введите ширину в пикселях:', state.canvasWidth);
    const h = prompt('Введите высоту в пикселях:', state.canvasHeight);
    if (w && h) {
      setCanvasDimensions(parseInt(w), parseInt(h));
    }
    return;
  }

  const [w, h] = val.split('x').map((n) => parseInt(n));
  setCanvasDimensions(w, h);
}

function setCanvasDimensions(w, h) {
  state.canvasWidth = w;
  state.canvasHeight = h;

  // Fit container on screen nicely
  const maxDim = 650;
  let contW, contH;
  if (w >= h) {
    contW = maxDim;
    contH = Math.round(maxDim * (h / w));
  } else {
    contH = maxDim;
    contW = Math.round(maxDim * (w / h));
  }

  elements.canvasContainer.style.width = `${contW}px`;
  elements.canvasContainer.style.height = `${contH}px`;

  renderCanvas();
  showToast(`Формат холста: ${w} × ${h} px`);
}

function onBackgroundTypeChange(val) {
  state.backgroundType = val;
  renderCanvas();
}

// --------------------------------------------------------------------------
// Export SVG & Clipboard
// --------------------------------------------------------------------------

async function downloadSvg() {
  try {
    const res = await fetch('/api/export/svg', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        canvas_width: state.canvasWidth,
        canvas_height: state.canvasHeight,
        items: state.canvasItems,
        palette_id: state.activePaletteId,
        background_type: state.backgroundType,
        size: state.activeSize,
        download: true,
      }),
    });

    const svgBlob = await res.blob();
    const url = URL.createObjectURL(svgBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `illustration_${state.activePaletteId}_${Date.now()}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('SVG файл успешно скачан!');
  } catch (err) {
    console.error('Error downloading SVG:', err);
    showToast('Ошибка скачивания SVG', 'error');
  }
}

async function copySvgCode() {
  try {
    const res = await fetch('/api/export/svg', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        canvas_width: state.canvasWidth,
        canvas_height: state.canvasHeight,
        items: state.canvasItems,
        palette_id: state.activePaletteId,
        background_type: state.backgroundType,
        size: state.activeSize,
      }),
    });

    const data = await res.json();
    if (data.svg) {
      await navigator.clipboard.writeText(data.svg);
      showToast('SVG код скопирован! Можно вставить в Figma (Ctrl+V)');
    }
  } catch (err) {
    console.error('Error copying SVG:', err);
    showToast('Ошибка копирования в буфер', 'error');
  }
}

// --------------------------------------------------------------------------
// Tab Navigation
// --------------------------------------------------------------------------

function switchTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach((btn, idx) => {
    const names = ['metaphor', 'components', 'palette', 'inspector'];
    btn.classList.toggle('active', names[idx] === tabName);
  });

  document.querySelectorAll('.tab-content').forEach((content) => {
    content.classList.remove('active');
  });

  const target = document.getElementById(`tab_${tabName}`);
  if (target) target.classList.add('active');
}

// --------------------------------------------------------------------------
// Modals & Uploads
// --------------------------------------------------------------------------

function openUploadModal() {
  document.getElementById('modal_upload_comp').style.display = 'flex';
}

function openPaletteModal() {
  document.getElementById('modal_upload_pal').style.display = 'flex';
}

function closeModals() {
  document.querySelectorAll('.modal-overlay').forEach((m) => (m.style.display = 'none'));
}

function onFileSelected(input) {
  if (input.files && input.files[0]) {
    const file = input.files[0];
    document.getElementById('upload_filename_label').textContent = file.name;
    const nameWithoutExt = file.name.replace(/\.svg$/i, '');
    document.getElementById('upload_comp_name').value = nameWithoutExt;
  }
}

function onPalFileSelected(input) {
  if (input.files && input.files[0]) {
    const file = input.files[0];
    document.getElementById('upload_pal_filename_label').textContent = file.name;
    const nameWithoutExt = file.name.replace(/\.svg$/i, '');
    document.getElementById('upload_pal_name').value = nameWithoutExt;
  }
}

async function submitComponentUpload() {
  const fileInput = document.getElementById('upload_main_file_input');
  const name = document.getElementById('upload_comp_name').value.trim();
  const size = document.getElementById('upload_comp_size').value;
  const tags = document.getElementById('upload_comp_tags').value.trim();

  if (!fileInput.files[0] || !name) {
    showToast('Выберите SVG файл и укажите название', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('main_file', fileInput.files[0]);
  formData.append('name', name);
  formData.append('size', size);
  formData.append('tags', tags);

  try {
    const res = await fetch('/api/library/upload', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message);
      closeModals();
      await loadLibrary();
    } else {
      showToast(data.error || 'Ошибка загрузки', 'error');
    }
  } catch (err) {
    console.error('Upload failed:', err);
    showToast('Ошибка соединения при загрузке', 'error');
  }
}

async function submitPaletteUpload() {
  const fileInput = document.getElementById('upload_pal_file_input');
  const name = document.getElementById('upload_pal_name').value.trim() || 'Пользовательская палитра';

  if (!fileInput.files[0]) {
    showToast('Выберите SVG файл палитры', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('name', name);

  try {
    const res = await fetch('/api/palettes', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Палитра «${name}» успешно добавлена!`);
      closeModals();
      await loadPalettes();
      selectPalette(data.palette.id);
    } else {
      showToast(data.error || 'Ошибка загрузки палитры', 'error');
    }
  } catch (err) {
    console.error('Palette upload failed:', err);
    showToast('Ошибка загрузки палитры', 'error');
  }
}

// --------------------------------------------------------------------------
// Toast Notifications
// --------------------------------------------------------------------------

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✓' : '⚠️'}</span><span>${message}</span>`;
  elements.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 200);
  }, 3200);
}
