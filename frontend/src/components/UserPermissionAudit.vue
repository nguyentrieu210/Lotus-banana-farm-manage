<script setup>
import {computed} from 'vue'
import DataTable from './DataTable.vue'
const props=defineProps({audit:Object})
const columns=computed(()=>[{field:'label',headerName:'Loại dữ liệu',minWidth:180},...Object.entries({read:'Xem',create:'Tạo',write:'Sửa',submit:'Ghi sổ',cancel:'Hủy',delete:'Xóa'}).map(([field,headerName])=>({field,headerName,minWidth:80,valueFormatter:p=>['submit','cancel'].includes(field)&&!p.data?.submittable?'—':p.value?'Có':'Không'}))])
</script>
<template><section v-if="audit" aria-label="Kiểm tra quyền đã lưu">
 <p class="user-hint">Quyền của cấu hình đã lưu. Lưu hồ sơ để cập nhật sau khi chỉnh vai trò hoặc phạm vi.</p>
 <h3>Quyền theo vai trò</h3>
 <DataTable :rows="audit.permissions" :columns="columns" storage-key="user-permission-audit"/>
 <h3>Quyền truy cập vườn thực tế</h3>
 <ul><li v-for="farm in audit.farms" :key="farm.name">{{farm.label}} · {{farm.name}} — {{farm.read?'Được xem':'Bị chặn'}}</li></ul>
 <h3>Điều kiện ký duyệt</h3>
 <p v-if="!audit.enabled" class="stock-error">Tài khoản đang bị khóa.</p>
 <p v-if="!audit.active_employee" class="stock-error">Chưa gắn nhân sự đang làm việc. Chọn nhân sự trong tab Hồ sơ để tài khoản xuất hiện trong danh sách người ký.</p>
 <ul><li v-for="step in audit.signing" :key="step.chain+step.step">{{step.chain_label}} · {{step.title}} — {{step.ready?'Đủ điều kiện theo role và tài khoản':!step.role_eligible?'Thiếu role: '+step.roles.join(' / '):'Chưa sẵn sàng: kiểm tra nhân sự và trạng thái tài khoản'}}</li></ul>
</section><p v-else class="user-hint">Lưu tài khoản trước khi kiểm tra quyền thực tế.</p></template>
