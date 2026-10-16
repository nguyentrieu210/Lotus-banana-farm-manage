<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { excelKey, filterExcelChoices, toggleExcelVisible, excelAppliedValues, excelPopupLeft, excelDefaultSelection } from '../excel-filter-state'

const props = defineProps({ params: { type: Object, required: true } })
const opened = ref(false)
const trigger = ref(null)
const popup = ref(null)
const searchInput = ref(null)
const search = ref('')
const selected = ref([])
const manualSelection = ref(false)
const position = ref({ top: '0px', left: '0px' })

const choices = computed(() => props.params.choices || [])
const active = computed(() => Array.isArray(props.params.selection))
const key = excelKey
const visible = computed(() => filterExcelChoices(choices.value, search.value))
const visibleKeys = computed(() => visible.value.map(row => key(row.value)))
const selectedVisibleCount = computed(() => visibleKeys.value.filter(k => selected.value.includes(k)).length)
const allVisible = computed(() => visibleKeys.value.length > 0 && selectedVisibleCount.value === visibleKeys.value.length)
const someVisible = computed(() => selectedVisibleCount.value > 0 && !allVisible.value)

function positionPopup() {
  if (!trigger.value || !popup.value) return
  const rect = trigger.value.getBoundingClientRect()
  const width = Math.min(312, window.innerWidth - 16)
  const height = Math.min(popup.value.offsetHeight || 370, window.innerHeight - 16)
  const top = rect.bottom + 6 + height <= window.innerHeight
    ? rect.bottom + 6 : Math.max(8, rect.top - height - 6)
  position.value = {
    top: Math.max(8, top) + 'px',
    // Open to the right of the filter button; clamp at the viewport edge.
    left: excelPopupLeft(rect.right, width, window.innerWidth) + 'px',
    width: width + 'px'
  }
}
async function open(event) {
  event.stopPropagation()
  if (opened.value) { close(); return }
  search.value = ''
  manualSelection.value = false
  selected.value = excelDefaultSelection(choices.value, props.params.selection, '')
  opened.value = true
  await nextTick()
  positionPopup()
  searchInput.value?.focus()
}
function close() { opened.value = false; search.value = '' }
function toggle(value) {
  manualSelection.value = true
  const k = key(value)
  selected.value = selected.value.includes(k) ? selected.value.filter(v => v !== k) : [...selected.value, k]
}
function selectVisible() {
  manualSelection.value = true
  selected.value = toggleExcelVisible(selected.value, visible.value, allVisible.value)
}
function apply() {
  props.params.apply(excelAppliedValues(choices.value, selected.value))
  close()
}
function clear() { props.params.apply(null); close() }
function outside(event) {
  if (opened.value && !popup.value?.contains(event.target) && !trigger.value?.contains(event.target)) close()
}
function onKeydown(event) {
  if (event.key === 'Escape' && opened.value) { event.stopPropagation(); close(); trigger.value?.focus() }
}
function onScroll() { if (opened.value) positionPopup() }
// Searching selects matching values by default. Once a user changes checkboxes,
// preserve that explicit selection while they search for additional values.
watch(search, value => {
  if (opened.value && !manualSelection.value)
    selected.value = excelDefaultSelection(choices.value, props.params.selection, value)
})
watch(() => props.params.selection, () => { if (!opened.value) return; close() })
onMounted(() => {
  document.addEventListener('pointerdown', outside)
  document.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', onScroll)
  window.addEventListener('scroll', onScroll, true)
})
onUnmounted(() => {
  document.removeEventListener('pointerdown', outside)
  document.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onScroll)
  window.removeEventListener('scroll', onScroll, true)
})
</script>

<template>
  <div class="excel-header">
    <button type="button" class="excel-sort" @click.stop="params.progressSort?.($event.shiftKey)" :title="'Sắp xếp '+params.displayName">{{ params.displayName }}</button>
    <button ref="trigger" type="button" class="excel-trigger" :class="{ active }"
      :aria-label="'Lọc cột '+params.displayName" :aria-expanded="opened" :aria-pressed="active"
      @click.stop="open">▾</button>
    <Teleport to="body">
      <div v-if="opened" ref="popup" class="excel-popup lotus-excel-popup" :style="position"
        :aria-label="'Lọc cột '+params.displayName" role="dialog" @click.stop @keydown.stop>
        <strong>Lọc: {{ params.displayName }}</strong>
        <input ref="searchInput" v-model="search" type="search" aria-label="Tìm giá trị trong cột" placeholder="Gõ để lọc giá trị…" autocomplete="off">
        <label class="excel-select-all">
          <input type="checkbox" :checked="allVisible" :indeterminate="someVisible" :disabled="!visible.length" @change="selectVisible">
          <span>Chọn tất cả kết quả ({{ visible.length }})</span>
        </label>
        <div class="excel-values" role="group" :aria-label="'Các giá trị cột '+params.displayName">
          <label v-for="row in visible" :key="key(row.value)">
            <input type="checkbox" :checked="selected.includes(key(row.value))" @change="toggle(row.value)">
            <span>{{ row.label ?? row.value ?? '(Trống)' }}</span>
          </label>
          <p v-if="!visible.length">Không tìm thấy giá trị phù hợp.</p>
        </div>
        <div class="excel-filter-count">Đã chọn {{ selected.length }} / {{ choices.length }} giá trị</div>
        <footer>
          <button type="button" @click="clear">Xóa lọc</button>
          <button type="button" class="excel-apply" @click="apply">Áp dụng</button>
        </footer>
      </div>
    </Teleport>
  </div>
</template>
