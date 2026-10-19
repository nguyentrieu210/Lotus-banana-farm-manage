<script setup>
import {ref} from 'vue'
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import {Select as UiSelect} from './ui/select'
import {FormField} from './ui/form-field'
import {Combobox} from './ui/combobox'
import {DatePicker,DateRangePicker} from './ui/date-picker'
import {DropdownMenu,DropdownMenuTrigger,DropdownMenuContent,DropdownMenuItem,DropdownMenuSeparator} from './ui/dropdown-menu'
import {Tooltip} from './ui/tooltip'
import {Popover,PopoverTrigger,PopoverContent} from './ui/popover'
import {Sheet} from './ui/sheet'
import {Pagination} from './ui/pagination'
import {Skeleton as UiSkeleton} from './ui/skeleton'
import {Toaster,toast} from './ui/toast'
import WorkspaceModal from './WorkspaceModal.vue'
import WorkspaceTabs from './WorkspaceTabs.vue'
import DesktopEmptyState from './DesktopEmptyState.vue'
import LotusIcon from './LotusIcon.vue'
import DataTable from './DataTable.vue'
import {useWorkspace} from '../workspace'
// Dev-only catalogue of the shared components (frontend/showcase.html, served by `npm run dev`, not built).
const {dark,toggleTheme}=useWorkspace()
const farms=[{value:'LOTUS-222',label:'Vườn Lô 222',subtitle:'Lotus Agritech',group:'Đồng Nai'},{value:'VIP-126',label:'Vườn VIP 126',subtitle:'Lotus Agritech',group:'Đồng Nai'},{value:'BD-01',label:'Bình Dương 01',group:'Bình Dương'}]
const farm=ref('VIP-126'),item=ref(''),date=ref('2026-10-19'),from=ref('2026-10-01'),to=ref('2026-10-19'),start=ref(0),start2=ref(100)
const stockRows=[{item:'Phân NPK',warehouse:'Kho tổng',qty:120},{item:'Bao buồng',warehouse:'Kho tổng',qty:4000},{item:'Dây buộc',warehouse:'Kho Vườn A',qty:35},{item:'Thuốc nấm',warehouse:'Kho Vườn A',qty:8},{item:'Phân NPK',warehouse:'Kho Vườn A',qty:60},{item:'Bao buồng',warehouse:'Kho Vườn B',qty:900}]
const stockColumns=[{field:'item',headerName:'Vật tư'},{field:'warehouse',headerName:'Kho'},{field:'qty',headerName:'Tồn'}]
const tab=ref('a'),modal=ref(false),sheet=ref(false),name=ref(''),nameError=ref('Nhập họ tên trước khi lưu.')
async function fetchItems(search){await new Promise(r=>setTimeout(r,250));return ['Phân NPK 16-16-8','Bao buồng chuối','Dây buộc','Thuốc phòng nấm'].filter(x=>x.toLowerCase().includes(search.toLowerCase())).map((label,i)=>({value:'VT-00'+(i+1),label}))}
</script>
<template>
 <div class="lotus-ui showcase">
  <header class="showcase__head"><h1>Bộ component Lotus</h1><UiButton variant="outline" @click="toggleTheme"><LotusIcon :name="dark?'sun':'moon'"/>{{dark?'Sáng':'Tối'}}</UiButton></header>
  <section><h2>Nút & thông báo</h2><div class="row">
   <UiButton>Lưu</UiButton><UiButton variant="outline">Hủy</UiButton><UiButton variant="ghost">Ghost</UiButton><UiButton variant="destructive">Xóa</UiButton><UiButton loading>Đang lưu</UiButton>
   <UiButton variant="outline" @click="toast.success('Đã lưu phiếu nháp.')">Toast thành công</UiButton>
   <UiButton variant="outline" @click="toast.error('Không lưu được: thiếu kho nhận.')">Toast lỗi</UiButton>
   <UiButton variant="outline" @click="toast({title:'Đã xóa dòng 3',tone:'info',action:{label:'Hoàn tác',run:()=>toast.success('Đã khôi phục dòng 3')}})">Toast + Hoàn tác</UiButton>
  </div></section>
  <section><h2>Biểu mẫu</h2><div class="grid">
   <FormField label="Họ và tên" required :error="name?'':nameError" v-slot="field"><UiInput v-bind="field" v-model="name" placeholder="Nguyễn Văn A"/></FormField>
   <FormField label="Vườn" hint="Gõ không dấu: “vuon lo”" v-slot="field"><Combobox v-bind="field" v-model="farm" :options="farms" hide-values label="Vườn"/></FormField>
   <FormField label="Vật tư (tải từ máy chủ)" v-slot="field"><Combobox v-bind="field" v-model="item" :fetch-options="fetchItems" allow-custom label="Vật tư"/></FormField>
   <FormField label="Ngày chứng từ" v-slot="field"><DatePicker v-bind="field" v-model="date" label="Ngày chứng từ"/></FormField>
   <FormField label="Khoảng ngày báo cáo" v-slot="field"><DateRangePicker v-bind="field" v-model:from="from" v-model:to="to"/></FormField>
   <FormField label="Trạng thái" v-slot="field"><UiSelect v-bind="field" model-value="Draft"><option value="Draft">Nháp</option><option value="Submitted">Đã duyệt</option></UiSelect></FormField>
  </div><p class="hint">Giá trị: {{farm}} · {{item}} · {{date}} · {{from}} → {{to}}</p></section>
  <section><h2>Menu, tooltip, popover, sheet</h2><div class="row">
   <DropdownMenu><DropdownMenuTrigger as-child><UiButton variant="outline">Thao tác<LotusIcon name="chevron-down"/></UiButton></DropdownMenuTrigger>
    <DropdownMenuContent><DropdownMenuItem><LotusIcon name="document"/>In phiếu</DropdownMenuItem><DropdownMenuItem><LotusIcon name="transfer"/>Chuyển kho</DropdownMenuItem><DropdownMenuSeparator/><DropdownMenuItem disabled>Hủy phiếu</DropdownMenuItem></DropdownMenuContent></DropdownMenu>
   <Tooltip content="Thu gọn thanh bên"><UiButton variant="ghost" size="icon" aria-label="Thu gọn thanh bên"><LotusIcon name="menu"/></UiButton></Tooltip>
   <Popover><PopoverTrigger as-child><UiButton variant="outline">Bộ lọc nhanh</UiButton></PopoverTrigger><PopoverContent><p style="margin:0 0 8px">Nội dung popover: bộ lọc, ghi chú…</p><UiButton size="sm">Áp dụng</UiButton></PopoverContent></Popover>
   <UiButton variant="outline" @click="sheet=true">Mở Sheet chi tiết</UiButton>
   <UiButton variant="outline" @click="modal=true">Mở hộp thoại có Combobox</UiButton>
  </div></section>
  <section><h2>Bảng (lọc cột, chế độ xem)</h2><DataTable :rows="stockRows" :columns="stockColumns" storage-key="showcase-stock"/></section>
  <section><h2>Tab, phân trang, tải, trống</h2>
   <WorkspaceTabs v-model="tab" :items="[{id:'a',label:'Tồn kho'},{id:'b',label:'Lịch sử'},{id:'c',label:'Nhập xuất'}]" label="Ví dụ tab"/>
   <Pagination v-model:start="start" :count="50" has-more/>
   <Pagination v-model:start="start2" :count="50" :total="1234"/>
   <div class="grid"><div><UiSkeleton style="height:34px;margin-bottom:8px"/><UiSkeleton style="height:34px;margin-bottom:8px"/><UiSkeleton style="height:34px"/></div>
   <DesktopEmptyState title="Chưa có phiếu nhập" description="Tạo phiếu đầu tiên hoặc đổi bộ lọc."><template #actions><UiButton size="sm">Tạo phiếu nhập</UiButton><UiButton size="sm" variant="outline">Xóa bộ lọc</UiButton></template></DesktopEmptyState></div>
  </section>
  <WorkspaceModal v-model="modal" title="Phiếu nhập kho" width="560px"><div class="grid"><FormField label="Vườn" v-slot="field"><Combobox v-bind="field" v-model="farm" :options="farms" hide-values label="Vườn"/></FormField><FormField label="Ngày nhập" v-slot="field"><DatePicker v-bind="field" v-model="date"/></FormField></div></WorkspaceModal>
  <Sheet v-model:open="sheet" title="Chi tiết phiếu PN-0012" description="Nhập kho từ đơn mua PO-0045"><p>Nội dung chi tiết bản ghi…</p><template #footer><UiButton variant="outline" @click="sheet=false">Đóng</UiButton><UiButton>Mở phiếu</UiButton></template></Sheet>
  <Toaster/>
 </div>
</template>
<style>
.showcase{min-height:100vh;padding:24px 32px;background:var(--lotus-page);color:var(--lotus-text);font-family:var(--lotus-font)}
.showcase__head{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}.showcase h1{font-size:22px;margin:0}
.showcase section{margin-bottom:20px;padding:16px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg);background:var(--lotus-surface)}
.showcase h2{font-size:15px;margin:0 0 12px}.showcase .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.showcase .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;align-items:start}.showcase .hint{color:var(--lotus-muted);font-size:12px}
</style>
