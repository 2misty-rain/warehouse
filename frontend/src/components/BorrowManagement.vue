<template>
  <div class="borrow-management">
    <div class="header">
      <el-button type="primary" @click="showBorrowDialog = true">
        <el-icon><Plus /></el-icon> 设备借出
      </el-button>
      <el-button @click="refreshAll">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
      <el-input v-model="searchText" placeholder="搜索设备号/借用人" clearable style="width: 220px; margin-left: 10px;" @input="loadBorrowRecords" />
      <el-select v-model="filterStatus" placeholder="筛选状态" clearable style="width: 120px; margin-left: 10px;" @change="loadBorrowRecords">
        <el-option label="借出中" value="borrowed"></el-option>
        <el-option label="已归还" value="returned"></el-option>
        <el-option label="逾期" value="overdue"></el-option>
      </el-select>
      <el-badge :value="overdueCount" :hidden="overdueCount === 0" style="margin-left: 10px;">
        <el-button type="danger" @click="showOverdueList">逾期未还</el-button>
      </el-badge>
      <el-button v-if="selectedRows.length > 0" type="success" @click="batchReturn" style="margin-left: 10px;">
        批量归还 ({{ selectedRows.length }})
      </el-button>
    </div>

    <el-table :data="borrowRecords" v-loading="loading" style="width: 100%" border stripe
      @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="50" :selectable="row => row.status !== 'returned'" />
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="device_id" label="设备号" width="140" sortable />
      <el-table-column label="类型" width="70">
        <template #default="{ row }">{{ deviceInfoMap[row.device_id]?.type || '-' }}</template>
      </el-table-column>
      <el-table-column label="版本" width="60">
        <template #default="{ row }">{{ deviceInfoMap[row.device_id]?.version || '-' }}</template>
      </el-table-column>
      <el-table-column prop="borrower" label="借用人" width="100" sortable />
      <el-table-column prop="borrow_date" label="借用时间" width="150" sortable>
        <template #default="{ row }">{{ row.borrow_date ? new Date(row.borrow_date).toLocaleString() : '-' }}</template>
      </el-table-column>
      <el-table-column prop="expected_return_date" label="预计归还" width="110" sortable>
        <template #default="{ row }">{{ row.expected_return_date || '-' }}</template>
      </el-table-column>
      <el-table-column prop="actual_return_date" label="实际归还" width="110" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="purpose" label="目的" min-width="130" show-overflow-tooltip />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status !== 'returned'" size="small" type="success" @click="showReturnDialog(row)">归还</el-button>
          <el-button size="small" @click="viewDetail(row)">详情</el-button>
          <el-button v-if="row.status === 'returned' || row.status === 'terminated'" size="small" type="danger" @click="deleteRecord(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      @current-change="handlePageChange"
      :current-page="currentPage" :page-size="pageSize"
      layout="total, prev, pager, next" :total="totalRecords"
      style="margin-top: 20px; text-align: right;" />

    <!-- 借出对话框 -->
    <el-dialog title="设备借出登记" v-model="showBorrowDialog" width="600px">
      <el-form :model="borrowForm" :rules="borrowRules" ref="borrowFormRef" label-width="120px">
        <el-form-item label="设备号" prop="device_id">
          <el-select v-model="borrowForm.device_id" placeholder="搜索设备号或归属人" filterable style="width: 100%;"
            @change="handleDeviceSelect">
            <el-option v-for="d in availableDevices" :key="d.device_id"
              :label="`${d.device_id} | ${d.version || '-'} | ${d.owner || '无归属'}`"
              :value="d.device_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="借用人" prop="borrower">
          <el-input v-model="borrowForm.borrower" placeholder="请输入借用人姓名" />
        </el-form-item>
        <el-form-item label="预计归还" prop="expected_return_date">
          <el-date-picker v-model="borrowForm.expected_return_date" type="date" placeholder="选择日期"
            format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="借用目的">
          <el-input v-model="borrowForm.purpose" type="textarea" :rows="2" placeholder="请说明借用目的" />
        </el-form-item>
        <el-form-item label="设备状态">
          <el-input v-model="borrowForm.condition_on_borrow" type="textarea" :rows="2" placeholder="借出时设备外观、功能状态" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="borrowForm.remarks" type="textarea" :rows="2" placeholder="其他备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBorrowDialog = false">取消</el-button>
        <el-button type="primary" @click="submitBorrow">确定借出</el-button>
      </template>
    </el-dialog>

    <!-- 归还对话框 -->
    <el-dialog title="设备归还登记" v-model="showReturnDialogVisible" width="600px">
      <el-alert v-if="returnRecord" :title="`${returnRecord.device_id} | 借用人: ${returnRecord.borrower}`" type="info" :closable="false" style="margin-bottom: 20px;" />
      <el-form :model="returnForm" ref="returnFormRef" label-width="120px">
        <el-form-item label="实际归还日期">
          <el-date-picker v-model="returnForm.actual_return_date" type="date" placeholder="选择日期"
            format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="归还时状态">
          <el-input v-model="returnForm.condition_on_return" type="textarea" :rows="2" placeholder="归还时设备状态" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="returnForm.remarks" type="textarea" :rows="2" placeholder="其他备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReturnDialogVisible = false">取消</el-button>
        <el-button type="success" @click="submitReturn">确认归还</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog title="借用记录详情" v-model="showDetailDialog" width="600px">
      <el-descriptions :column="1" border v-if="detailRecord">
        <el-descriptions-item label="设备号">{{ detailRecord.device_id }}</el-descriptions-item>
        <el-descriptions-item label="借用人">{{ detailRecord.borrower }}</el-descriptions-item>
        <el-descriptions-item label="借用时间">{{ detailRecord.borrow_date ? new Date(detailRecord.borrow_date).toLocaleString() : '-' }}</el-descriptions-item>
        <el-descriptions-item label="预计归还">{{ detailRecord.expected_return_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="实际归还">{{ detailRecord.actual_return_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="getStatusType(detailRecord.status)">{{ getStatusText(detailRecord.status) }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="目的">{{ detailRecord.purpose || '-' }}</el-descriptions-item>
        <el-descriptions-item label="借出状态">{{ detailRecord.condition_on_borrow || '-' }}</el-descriptions-item>
        <el-descriptions-item label="归还状态">{{ detailRecord.condition_on_return || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ detailRecord.remarks || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 逾期列表 -->
    <el-dialog title="逾期未还" v-model="showOverdueDialog" width="800px">
      <el-table :data="overdueRecords" border stripe>
        <el-table-column prop="device_id" label="设备号" width="140" />
        <el-table-column prop="borrower" label="借用人" width="100" />
        <el-table-column prop="borrow_date" label="借用时间" width="150">
          <template #default="{ row }">{{ new Date(row.borrow_date).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="expected_return_date" label="应还日期" width="110" />
        <el-table-column prop="purpose" label="目的" min-width="130" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }"><el-button size="small" type="success" @click="showReturnDialog(row)">归还</el-button></template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { borrowAPI, inventoryAPI } from '../api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Refresh } from '@element-plus/icons-vue';

export default {
  name: 'BorrowManagement',
  components: { Plus, Refresh },
  setup() {
    const loading = ref(false);
    const borrowRecords = ref([]);
    const currentPage = ref(1);
    const pageSize = ref(10);
    const totalRecords = ref(0);
    const filterStatus = ref('');
    const searchText = ref('');
    const overdueCount = ref(0);
    const deviceInfoMap = ref({});
    const selectedRows = ref([]);

    const showBorrowDialog = ref(false);
    const showReturnDialogVisible = ref(false);
    const showDetailDialog = ref(false);
    const showOverdueDialog = ref(false);
    const returnRecord = ref(null);
    const detailRecord = ref(null);
    const overdueRecords = ref([]);
    const availableDevices = ref([]);

    const borrowForm = ref({ device_id: '', borrower: '', expected_return_date: null, purpose: '', condition_on_borrow: '', remarks: '' });
    const returnForm = ref({ actual_return_date: new Date().toISOString().split('T')[0], condition_on_return: '', remarks: '' });
    const borrowFormRef = ref(null);
    const borrowRules = {
      device_id: [{ required: true, message: '请选择设备', trigger: 'change' }],
      borrower: [{ required: true, message: '请输入借用人', trigger: 'blur' }]
    };

    const refreshAll = () => { loadBorrowRecords(); loadDeviceInfoMap(); loadOverdueCount(); };

    const loadDeviceInfoMap = async () => {
      try {
        const response = await inventoryAPI.getAll({ skip: 0, limit: 2000 });
        const devices = response.items || response;
        const map = {};
        devices.forEach(d => { map[d.device_id] = d; });
        deviceInfoMap.value = map;
        availableDevices.value = devices.filter(d => !d.borrower);
      } catch (error) { console.error('加载设备信息失败:', error); }
    };

    const loadBorrowRecords = async () => {
      loading.value = true;
      try {
        const params = { skip: (currentPage.value - 1) * pageSize.value, limit: pageSize.value, search: searchText.value };
        if (filterStatus.value) params.status = filterStatus.value;
        const data = await borrowAPI.getList(params);
        borrowRecords.value = data.items || data;
        totalRecords.value = data.total || (data.items || data).length;
      } catch (error) { ElMessage.error('加载借用记录失败'); }
      finally { loading.value = false; }
    };

    const loadOverdueCount = async () => {
      try { const data = await borrowAPI.getOverdue(); overdueCount.value = data.count; }
      catch (error) { console.error('加载逾期数据失败:', error); }
    };

    const handleSelectionChange = (rows) => { selectedRows.value = rows; };

    const handleDeviceSelect = (deviceId) => {
      const device = availableDevices.value.find(d => d.device_id === deviceId);
      if (device?.borrower) ElMessage.warning(`该设备当前由 ${device.borrower} 领用`);
    };

    const submitBorrow = async () => {
      try {
        await borrowFormRef.value.validate();
        await borrowAPI.borrow(borrowForm.value);
        ElMessage.success('设备借出成功');
        showBorrowDialog.value = false;
        borrowForm.value = { device_id: '', borrower: '', expected_return_date: null, purpose: '', condition_on_borrow: '', remarks: '' };
        refreshAll();
      } catch (error) {
        if (error.message) ElMessage.error(error.message);
        else ElMessage.error('借出设备失败');
      }
    };

    const showReturnDialog = (record) => {
      returnRecord.value = record;
      returnForm.value = { actual_return_date: new Date().toISOString().split('T')[0], condition_on_return: '', remarks: '' };
      showReturnDialogVisible.value = true;
    };

    const submitReturn = async () => {
      try {
        await borrowAPI.return(returnRecord.value.id, returnForm.value);
        ElMessage.success('设备归还成功');
        showReturnDialogVisible.value = false;
        showOverdueDialog.value = false;
        refreshAll();
      } catch (error) { ElMessage.error('归还设备失败'); }
    };

    const batchReturn = async () => {
      try {
        await ElMessageBox.confirm(`确认批量归还 ${selectedRows.value.length} 台设备？`, '批量归还', { type: 'info' });
        for (const row of selectedRows.value) {
          await borrowAPI.return(row.id, { actual_return_date: new Date().toISOString().split('T')[0] });
        }
        ElMessage.success(`成功归还 ${selectedRows.value.length} 台设备`);
        selectedRows.value = [];
        refreshAll();
      } catch (error) {
        if (error !== 'cancel') ElMessage.error('批量归还失败');
      }
    };

    const deleteRecord = async (row) => {
      try {
        await ElMessageBox.confirm(`确认删除借用记录 #${row.id} (${row.device_id})？此操作不可恢复。`, '确认删除', { type: 'warning' });
        await borrowAPI.delete(row.id);
        ElMessage.success('借用记录已删除');
        loadBorrowRecords();
      } catch (error) {
        if (error !== 'cancel') ElMessage.error('删除失败');
      }
    };

    const viewDetail = (record) => { detailRecord.value = record; showDetailDialog.value = true; };

    const showOverdueList = async () => {
      try { const data = await borrowAPI.getOverdue(); overdueRecords.value = data.records; showOverdueDialog.value = true; }
      catch (error) { ElMessage.error('加载逾期列表失败'); }
    };

    const handlePageChange = (page) => { currentPage.value = page; loadBorrowRecords(); };

    const getStatusType = (s) => ({ borrowed: 'warning', returned: 'success', overdue: 'danger' }[s] || 'info');
    const getStatusText = (s) => ({ borrowed: '借出中', returned: '已归还', overdue: '逾期', terminated: '已终止' }[s] || s);

    onMounted(() => refreshAll());

    return {
      loading, borrowRecords, currentPage, pageSize, totalRecords, filterStatus, searchText,
      overdueCount, deviceInfoMap, selectedRows, showBorrowDialog, showReturnDialogVisible,
      showDetailDialog, showOverdueDialog, returnRecord, detailRecord, overdueRecords,
      availableDevices, borrowForm, returnForm, borrowFormRef, borrowRules,
      handleSelectionChange, loadBorrowRecords, handleDeviceSelect, submitBorrow,
      showReturnDialog, submitReturn, batchReturn, deleteRecord, viewDetail,
      showOverdueList, refreshAll, handlePageChange, getStatusType, getStatusText
    };
  }
};
</script>

<style scoped>
.borrow-management { padding: 20px; }
.header { margin-bottom: 20px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
</style>
