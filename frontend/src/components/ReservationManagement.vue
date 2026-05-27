<template>
  <div class="reservation">
    <div class="header">
      <el-button type="primary" @click="showCreateDialog = true">提交出库申请</el-button>
      <el-button @click="loadReservations">刷新</el-button>
      <span style="margin-left: 16px; color: #909399;" v-if="isAdmin && pendingCount > 0">
        待处理: <strong style="color: #E6A23C;">{{ pendingCount }} 条</strong>
      </span>
    </div>

    <el-table :data="reservationList" v-loading="loading" border stripe style="width: 100%">
      <el-table-column prop="id" label="编号" width="60" />
      <el-table-column prop="applicant" label="申请人" width="100" />
      <el-table-column prop="client_name" label="甲方" width="120" />
      <el-table-column prop="quantity" label="需求数量" width="80" />
      <el-table-column label="版本/包装" width="120">
        <template #default="{ row }">
          {{ row.version_req || '-' }} / {{ row.packaging_req || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="sales_person" label="销售" width="100" />
      <el-table-column prop="required_date" label="需求日期" width="110">
        <template #default="{ row }">
          {{ row.required_date || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="purpose" label="用途" min-width="150" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="分配设备" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.assigned_devices ? JSON.parse(row.assigned_devices).join(', ') : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" v-if="isAdmin">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" size="small" type="primary" @click="openApprove(row)">
            分配出库
          </el-button>
          <el-button v-if="row.status === 'pending'" size="small" type="danger" @click="openReject(row)">
            驳回
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 提交申请对话框 -->
    <el-dialog title="提交出库申请" v-model="showCreateDialog" width="500px">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="100px">
        <el-form-item label="需求数量" prop="quantity">
          <el-input-number v-model="createForm.quantity" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="版本要求">
          <el-select v-model="createForm.version_req" placeholder="不限" clearable>
            <el-option label="WiFi" value="WiFi" />
            <el-option label="4G" value="4G" />
          </el-select>
        </el-form-item>
        <el-form-item label="包装要求">
          <el-select v-model="createForm.packaging_req" placeholder="不限" clearable>
            <el-option label="简约" value="简约" />
            <el-option label="精品" value="精品" />
          </el-select>
        </el-form-item>
        <el-form-item label="甲方" prop="client_name">
          <el-input v-model="createForm.client_name" placeholder="归属方名称" />
        </el-form-item>
        <el-form-item label="销售" prop="sales_person">
          <el-input v-model="createForm.sales_person" placeholder="销售人员" />
        </el-form-item>
        <el-form-item label="需求日期" prop="required_date">
          <el-date-picker v-model="createForm.required_date" type="date"
            placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="用途说明">
          <el-input v-model="createForm.purpose" type="textarea" placeholder="用途说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitCreate" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>

    <!-- 分配设备对话框（审批+出库） -->
    <el-dialog title="分配设备出库" v-model="showApproveDialog" width="700px">
      <el-alert title="申请详情" type="info" :closable="false" style="margin-bottom: 16px;">
        <p>需求: {{ approvingRow?.quantity }}台 | 版本: {{ approvingRow?.version_req || '不限' }} |
           包装: {{ approvingRow?.packaging_req || '不限' }} | 甲方: {{ approvingRow?.client_name }}</p>
        <p>销售: {{ approvingRow?.sales_person }} | 日期: {{ approvingRow?.required_date || '未指定' }}</p>
      </el-alert>
      <el-form label-width="100px">
        <el-form-item label="选择设备">
          <el-select v-model="approveForm.assigned_devices" multiple filterable
            placeholder="从可用库存中选择设备" style="width: 100%">
            <el-option v-for="d in availableDevices" :key="d.device_id"
              :label="`${d.device_id} (${d.version || '-'}/${d.type || '-'}/${d.packaging || '-'})`"
              :value="d.device_id" />
          </el-select>
          <div style="color: #909399; font-size: 12px; margin-top: 4px;">
            已选 {{ approveForm.assigned_devices.length }} / 需求 {{ approvingRow?.quantity }} 台
          </div>
        </el-form-item>
        <el-form-item label="管理员备注">
          <el-input v-model="approveForm.admin_remarks" type="textarea" placeholder="可选备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApproveDialog = false">取消</el-button>
        <el-button type="primary" @click="submitApprove" :loading="processing">
          确认分配并出库
        </el-button>
      </template>
    </el-dialog>

    <!-- 驳回对话框 -->
    <el-dialog title="驳回申请" v-model="showRejectDialog" width="400px">
      <el-form label-width="100px">
        <el-form-item label="驳回原因">
          <el-input v-model="rejectForm.admin_remarks" type="textarea" placeholder="填写驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRejectDialog = false">取消</el-button>
        <el-button type="danger" @click="submitReject" :loading="processing">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, reactive, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { reservationAPI, inventoryAPI } from '../api';

export default {
  name: 'ReservationManagement',
  setup() {
    const reservationList = ref([]);
    const loading = ref(false);
    const submitting = ref(false);
    const processing = ref(false);
    const pendingCount = ref(0);
    const availableDevices = ref([]);

    const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
    const isAdmin = computed(() => userInfo.role === 'admin');

    const showCreateDialog = ref(false);
    const showApproveDialog = ref(false);
    const showRejectDialog = ref(false);
    const approvingRow = ref(null);
    const createFormRef = ref(null);

    const createForm = reactive({
      quantity: 1,
      version_req: '',
      packaging_req: '',
      client_name: '',
      sales_person: '',
      required_date: null,
      purpose: ''
    });
    const createRules = {
      quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }],
      client_name: [{ required: true, message: '请输入甲方名称', trigger: 'blur' }],
      sales_person: [{ required: true, message: '请输入销售', trigger: 'blur' }],
      required_date: [{ required: true, message: '请选择需求日期', trigger: 'change' }]
    };

    const approveForm = reactive({
      assigned_devices: [],
      admin_remarks: ''
    });
    const rejectForm = reactive({ admin_remarks: '' });

    const loadReservations = async () => {
      loading.value = true;
      try {
        const res = await reservationAPI.getList();
        reservationList.value = res.items || res;
        if (isAdmin.value) {
          try { const c = await reservationAPI.getPendingCount(); pendingCount.value = c.count; } catch {}
        }
      } catch (e) { ElMessage.error('加载失败'); }
      finally { loading.value = false; }
    };

    const loadAvailableDevices = async () => {
      try {
        const res = await inventoryAPI.getAll({ skip: 0, limit: 1000 });
        const items = res.items || res;
        availableDevices.value = items.filter(d => !d.borrower && d.device_attribute !== '商机交付');
      } catch {}
    };

    const submitCreate = async () => {
      const valid = await createFormRef.value.validate().catch(() => false);
      if (!valid) return;
      submitting.value = true;
      try {
        await reservationAPI.create(createForm);
        ElMessage.success('申请已提交');
        showCreateDialog.value = false;
        Object.keys(createForm).forEach(k => createForm[k] = k === 'quantity' ? 1 : (k === 'required_date' ? null : ''));
        loadReservations();
      } catch (e) {
        ElMessage.error(e.response?.data?.detail || '提交失败');
      } finally { submitting.value = false; }
    };

    const openApprove = (row) => {
      approvingRow.value = row;
      approveForm.assigned_devices = [];
      approveForm.admin_remarks = '';
      loadAvailableDevices();
      showApproveDialog.value = true;
    };

    const submitApprove = async () => {
      if (approveForm.assigned_devices.length === 0) {
        ElMessage.warning('请至少选择一台设备');
        return;
      }
      processing.value = true;
      try {
        const res = await reservationAPI.approve(approvingRow.value.id, approveForm);
        ElMessage.success(res.message || '出库完成');
        showApproveDialog.value = false;
        loadReservations();
        window.dispatchEvent(new CustomEvent('ai-data-changed'));
      } catch (e) {
        ElMessage.error(e.response?.data?.detail || '操作失败');
      } finally { processing.value = false; }
    };

    const openReject = (row) => {
      approvingRow.value = row;
      rejectForm.admin_remarks = '';
      showRejectDialog.value = true;
    };

    const submitReject = async () => {
      processing.value = true;
      try {
        await reservationAPI.reject(approvingRow.value.id, rejectForm);
        ElMessage.success('已驳回');
        showRejectDialog.value = false;
        loadReservations();
      } catch (e) {
        ElMessage.error(e.response?.data?.detail || '操作失败');
      } finally { processing.value = false; }
    };

    const statusType = (s) => ({ pending: 'warning', approved: 'success', fulfilled: '', rejected: 'danger' }[s] || 'info');
    const statusText = (s) => ({ pending: '待处理', approved: '已审批', fulfilled: '已出库', rejected: '已驳回' }[s] || s);

    onMounted(() => {
      loadReservations();
    });

    return {
      reservationList, loading, submitting, processing, pendingCount,
      availableDevices, isAdmin, showCreateDialog, showApproveDialog, showRejectDialog,
      approvingRow, createFormRef, createForm, createRules, approveForm, rejectForm,
      loadReservations, submitCreate, openApprove, submitApprove, openReject, submitReject,
      statusType, statusText
    };
  }
};
</script>

<style scoped>
.reservation { padding: 20px; }
.header { margin-bottom: 20px; }
</style>
