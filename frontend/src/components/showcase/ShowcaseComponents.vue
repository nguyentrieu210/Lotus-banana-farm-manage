<script setup>
import {ref} from 'vue'
import {Button as UiButton} from '../ui/button'
import {Input as UiInput} from '../ui/input'
import {Select as UiSelect} from '../ui/select'
import {Textarea as UiTextarea} from '../ui/textarea'
import {Checkbox} from '../ui/checkbox'
import {FormField} from '../ui/form-field'
import {Combobox} from '../ui/combobox'
import {DatePicker,DateRangePicker} from '../ui/date-picker'
import {DropdownMenu,DropdownMenuTrigger,DropdownMenuContent,DropdownMenuItem,DropdownMenuSeparator} from '../ui/dropdown-menu'
import {Tooltip} from '../ui/tooltip'
import {Popover,PopoverTrigger,PopoverContent} from '../ui/popover'
import {Sheet} from '../ui/sheet'
import {Pagination} from '../ui/pagination'
import {Skeleton as UiSkeleton} from '../ui/skeleton'
import {toast} from '../ui/toast'
import {StatusChip} from '../ui/status-chip'
import {Banner} from '../ui/banner'
import {StatTile} from '../ui/stat-tile'
import {Progress,ProgressRing} from '../ui/progress'
import {Switch} from '../ui/switch'
import {Segmented} from '../ui/segmented'
import {NumberStepper} from '../ui/number-stepper'
import {Avatar} from '../ui/avatar'
import {Steps} from '../ui/steps'
import {Timeline} from '../ui/timeline'
import {DescriptionList} from '../ui/description-list'
import WorkspaceModal from '../WorkspaceModal.vue'
import WorkspaceTabs from '../WorkspaceTabs.vue'
import DesktopEmptyState from '../DesktopEmptyState.vue'
import LotusIcon from '../LotusIcon.vue'
import {STATUS_KINDS} from '../../ui-status.js'
import {lotEvents} from './sample-data.js'
// Thành phần: every primitive of the kit with its variants and states (spec 004, User Story 3, SC-003).
const farms=[{value:'V1',label:'Vườn mẫu 1',group:'Đồng Nai'},{value:'V2',label:'Vườn mẫu 2',group:'Đồng Nai'},{value:'V3',label:'Vườn mẫu 3',group:'Bình Dương'}]
const farm=ref('V1'),date=ref('2026-11-10'),from=ref('2026-11-01'),to=ref('2026-11-10'),name=ref(''),note=ref(''),agree=ref(true)
const tab=ref('a'),view=ref('week'),outdoor=ref(false),notify=ref(true),bunches=ref(12),kg=ref(1640.5),empty=ref(null),start=ref(100)
const modal=ref(false),sheet=ref(false)
const steps=[{label:'Lập phiếu',meta:'Thư · 08:12',state:'done'},{label:'Trưởng phòng',meta:'Hồng · 09:40',state:'done'},{label:'Kế toán',meta:'Đang chờ ký',state:'current'},{label:'Giám đốc',state:'waiting'}]
const stepsReturned=[{label:'Lập phiếu',meta:'An · 07:55',state:'done'},{label:'Thủ kho',meta:'Trả lại: thiếu ảnh phiếu giao',state:'returned'},{label:'Kế toán',state:'waiting'}]
const details=[{label:'Số chứng từ',value:'PO-2026-00118'},{label:'Ngày',value:'10/11/2026'},{label:'Nhà cung cấp',value:'Đại lý Phân bón Minh Phát'},{label:'Kho nhận',value:'Kho tổng'},{label:'Trạng thái',key:'state'},{label:'Ghi chú',value:''},{label:'Diễn giải',value:'Phân NPK 16-16-8 cho khu A và B, giao hai đợt',wide:true}]
const kinds=Object.keys(STATUS_KINDS)
</script>
<template>
 <div class="sc-stack">
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Nút</h3><span class="lotus-caps">Đỏ đặc chỉ cho một hành động chính</span></header>
   <div class="lotus-card__body sc-stack-sm">
    <div class="sc-row"><UiButton><LotusIcon name="plus"/>Tạo phiếu nhập</UiButton><UiButton variant="outline">Lưu nháp</UiButton><UiButton variant="secondary">Phụ</UiButton><UiButton variant="soft">Nhẹ</UiButton><UiButton variant="ghost">Mờ</UiButton><UiButton variant="link">Liên kết</UiButton><UiButton loading>Đang lưu</UiButton><UiButton disabled>Vô hiệu</UiButton></div>
    <div class="sc-row"><UiButton>Lưu</UiButton><UiButton variant="destructive"><LotusIcon name="trash"/>Xóa dòng</UiButton><UiButton variant="destructive"><LotusIcon name="ban"/>Hủy chứng từ</UiButton><UiButton variant="danger"><LotusIcon name="trash"/>Xóa hẳn (trong hộp xác nhận)</UiButton></div>
    <div class="sc-row"><UiButton size="sm">Nhỏ</UiButton><UiButton>Vừa</UiButton><UiButton size="lg">Lớn</UiButton><Tooltip content="In phiếu"><UiButton size="icon" variant="outline" aria-label="In phiếu"><LotusIcon name="printer"/></UiButton></Tooltip><Tooltip content="Thêm"><UiButton size="icon" variant="ghost" aria-label="Thêm"><LotusIcon name="more"/></UiButton></Tooltip></div>
   </div>
  </article>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Nhập liệu</h3></header>
   <div class="lotus-card__body sc-form">
    <FormField label="Họ và tên" required :error="name?'':'Nhập họ tên trước khi lưu.'" v-slot="field"><UiInput v-bind="field" v-model="name" placeholder="Nguyễn Văn A"/></FormField>
    <FormField label="Vườn" hint="Gõ không dấu cũng tìm được" v-slot="field"><Combobox v-bind="field" v-model="farm" :options="farms" hide-values label="Vườn"/></FormField>
    <FormField label="Ngày chứng từ" v-slot="field"><DatePicker v-bind="field" v-model="date" label="Ngày chứng từ"/></FormField>
    <FormField label="Khoảng ngày" v-slot="field"><DateRangePicker v-bind="field" v-model:from="from" v-model:to="to"/></FormField>
    <FormField label="Trạng thái" v-slot="field"><UiSelect v-bind="field" model-value="Draft"><option value="Draft">Nháp</option><option value="Submitted">Đã duyệt</option></UiSelect></FormField>
    <FormField label="Ghi chú" v-slot="field"><UiTextarea v-bind="field" v-model="note" placeholder="Ghi chú cho kế toán…"/></FormField>
    <div class="sc-field"><span class="sc-label">Số buồng cắt bắp</span><NumberStepper v-model="bunches" label="Số buồng cắt bắp" unit="buồng"/></div>
    <div class="sc-field"><span class="sc-label">Khối lượng (số lẻ)</span><NumberStepper v-model="kg" label="Khối lượng" unit="kg" :step="0.5" :decimals="1"/></div>
    <div class="sc-field"><span class="sc-label">Chưa nhập (để trống, không phải 0)</span><NumberStepper v-model="empty" label="Số buồng hủy" unit="buồng"/></div>
    <div class="sc-field"><span class="sc-label">Chọn theo đoạn</span><Segmented v-model="view" label="Kỳ báo cáo" :options="[{value:'morning',label:'Sáng nay'},{value:'week',label:'Tuần',count:46},{value:'month',label:'Tháng'}]"/></div>
    <div class="sc-field"><span class="sc-label">Công tắc và hộp kiểm</span><Switch v-model="outdoor" label="Chế độ ngoài trời"/><Switch v-model="notify" label="Nhận thông báo duyệt"/><label class="sc-check"><Checkbox v-model="agree"/>Đã kiểm hàng đủ</label></div>
   </div>
  </article>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Nhãn trạng thái dùng chung</h3><span class="lotus-caps">Cùng trạng thái, cùng nhãn ở mọi phân hệ</span></header>
   <div class="lotus-card__body sc-stack-sm">
    <div class="sc-row"><StatusChip v-for="k in kinds" :key="k" :status="k"/></div>
    <div class="sc-row"><StatusChip status="Draft" size="sm"/><StatusChip status="Approved" size="sm"/><StatusChip status="Overdue" size="sm"/><StatusChip status="Approved" solid/><StatusChip status="Overdue" solid/><StatusChip status="Quarantine" solid size="lg"/><StatusChip status="Một trạng thái lạ"/></div>
   </div>
  </article>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Thông báo trong trang</h3></header>
   <div class="lotus-card__body sc-stack-sm">
    <Banner tone="info" title="Kỳ tháng 10 đã khóa sổ">Chứng từ ngày trong tháng 10 chỉ xem được. Muốn sửa, nhờ kế toán trưởng mở kỳ.</Banner>
    <Banner tone="success" title="Đã gửi báo cáo ngày của tổ 01">Đội trưởng sẽ xác nhận trước 18:00.</Banner>
    <Banner tone="warning" title="Thiếu ảnh phiếu giao hàng" dismissible>Thủ kho cần ảnh phiếu có chữ ký người giao trước khi xác nhận nhập kho.<template #actions><UiButton size="sm" variant="outline"><LotusIcon name="upload"/>Tải ảnh lên</UiButton></template></Banner>
    <Banner tone="danger" title="Lô C1 đang cách ly thuốc">Không ghi được thu hoạch trước ngày 14/11/2026.</Banner>
    <div class="sc-row"><UiButton variant="outline" @click="toast.success('Đã lưu phiếu nháp.')">Thông báo nổi: thành công</UiButton><UiButton variant="outline" @click="toast.error('Không lưu được: thiếu kho nhận.')">Thông báo nổi: lỗi</UiButton><UiButton variant="outline" @click="toast({title:'Đã xóa dòng 3',tone:'info',action:{label:'Hoàn tác',run:()=>toast.success('Đã khôi phục dòng 3')}})">Có Hoàn tác</UiButton></div>
   </div>
  </article>
  <div class="sc-grid-2">
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Ô số liệu</h3></header>
    <div class="lotus-card__body sc-stat-row">
     <StatTile label="Buồng thu tuần này" :value="6640" unit="buồng" icon="bunch" tone="success" :delta="120" delta-label="so với tuần trước"/>
     <StatTile label="Chi phí phân bón" :value="128450000" unit="đ" icon="wallet" tone="primary" :delta="-4.2" :delta-digits="1" delta-unit="%" good-when="down" delta-label="so với kế hoạch"/>
     <StatTile label="Lô quá hạn chăm sóc" :value="9" unit="lô" icon="alert" tone="danger" :delta="3" good-when="down" delta-label="so với hôm qua"/>
     <StatTile label="Dự thu so với thực tế" :value="null" icon="trending" tone="info" missing="Chưa có bản chốt của tuần này"/>
    </div>
   </article>
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Tiến độ</h3></header>
    <div class="lotus-card__body sc-stack-sm">
     <Progress :value="38" :max="64" label="Lô đã báo cáo hôm nay" value-text="38 / 64 lô" tone="info"/>
     <Progress :value="6640" :max="6900" label="Thu hoạch so với dự thu" value-text="96%" tone="success"/>
     <Progress :value="9" :max="64" label="Lô quá hạn" value-text="9 lô" tone="danger"/>
     <div class="sc-row"><ProgressRing :value="38" :max="64" label="Lô đã báo cáo" tone="info"/><ProgressRing :value="96" label="Thu so với dự thu" tone="success"/><ProgressRing :value="14" label="Lô quá hạn" tone="danger"/><ProgressRing :value="75" :size="64" :stroke="7" label="Hoàn thành vòng cắt lá"/></div>
    </div>
   </article>
  </div>
  <div class="sc-grid-2">
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Các bước duyệt và ký</h3></header>
    <div class="lotus-card__body sc-stack"><Steps :steps="steps" label="Duyệt đơn mua PO-2026-00118"/><Steps :steps="stepsReturned" label="Nhập kho" vertical/></div>
   </article>
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Dòng thời gian của lô A5</h3></header>
    <div class="lotus-card__body"><Timeline :items="lotEvents" label="Việc trên lô A5"/></div>
   </article>
  </div>
  <div class="sc-grid-2">
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Chi tiết chứng từ</h3></header>
    <div class="lotus-card__body"><DescriptionList :items="details"><template #value-state><StatusChip status="To Sign" label="Chờ kế toán ký" size="sm"/></template></DescriptionList></div>
   </article>
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Người, tab, phân trang, tải, trống</h3></header>
    <div class="lotus-card__body sc-stack-sm">
     <div class="sc-row"><Avatar name="Nguyễn Văn An"/><Avatar name="Trần Thị Hồng"/><Avatar name="Lê Văn Bình"/><Avatar name="Phạm Minh Thư" size="lg"/><Avatar name="Võ Lan" size="sm"/></div>
     <WorkspaceTabs v-model="tab" :items="[{id:'a',label:'Tồn kho'},{id:'b',label:'Lịch sử'},{id:'c',label:'Nhập xuất'}]" label="Ví dụ tab"/>
     <Pagination :size-selectable="false" v-model:start="start" :count="50" :total="1234"/>
     <div class="sc-grid-2"><div class="sc-stack-sm"><UiSkeleton style="height:34px"/><UiSkeleton style="height:34px"/><UiSkeleton style="height:34px"/></div><DesktopEmptyState title="Chưa có phiếu nhập" description="Tạo phiếu đầu tiên hoặc đổi bộ lọc."><template #actions><UiButton size="sm"><LotusIcon name="plus"/>Tạo phiếu nhập</UiButton></template></DesktopEmptyState></div>
    </div>
   </article>
  </div>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Lớp nổi: menu, chú thích, hộp nổi, ngăn kéo, hộp thoại</h3></header>
   <div class="lotus-card__body sc-row">
    <DropdownMenu><DropdownMenuTrigger as-child><UiButton variant="outline">Thao tác<LotusIcon name="chevron-down"/></UiButton></DropdownMenuTrigger><DropdownMenuContent><DropdownMenuItem><LotusIcon name="printer"/>In phiếu</DropdownMenuItem><DropdownMenuItem><LotusIcon name="transfer"/>Chuyển kho</DropdownMenuItem><DropdownMenuSeparator/><DropdownMenuItem disabled>Hủy phiếu</DropdownMenuItem></DropdownMenuContent></DropdownMenu>
    <Popover><PopoverTrigger as-child><UiButton variant="outline"><LotusIcon name="filter"/>Bộ lọc nhanh</UiButton></PopoverTrigger><PopoverContent><p style="margin:0 0 8px">Bộ lọc, ghi chú ngắn…</p><UiButton size="sm">Áp dụng</UiButton></PopoverContent></Popover>
    <UiButton variant="outline" @click="sheet=true">Mở ngăn kéo chi tiết</UiButton>
    <UiButton variant="outline" @click="modal=true">Mở hộp thoại nhập</UiButton>
   </div>
  </article>
  <WorkspaceModal v-model="modal" title="Phiếu nhập kho" width="560px"><div class="sc-form"><FormField label="Vườn" v-slot="field"><Combobox v-bind="field" v-model="farm" :options="farms" hide-values label="Vườn"/></FormField><FormField label="Ngày nhập" v-slot="field"><DatePicker v-bind="field" v-model="date"/></FormField></div></WorkspaceModal>
  <Sheet v-model:open="sheet" title="Phiếu PN-0012" description="Nhập kho từ đơn mua PO-2026-00118"><DescriptionList :items="details" :columns="1"><template #value-state><StatusChip status="Approved" size="sm"/></template></DescriptionList><template #footer><UiButton variant="outline" @click="sheet=false">Đóng</UiButton><UiButton>Mở phiếu</UiButton></template></Sheet>
 </div>
</template>
