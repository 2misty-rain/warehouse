<template>
  <div class="iot-management">
    <div class="page-header">
      <h2>物联网卡管理</h2>
      <p>管理4G设备的物联网卡开卡/关卡状态</p>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-select v-model="filterStatus" placeholder="IoT卡状态" clearable @change="fetchData">
          <el-option label="已开卡" value="开卡" />
          <el-option label="已关卡" value="关卡" />
          <el-option label="未设置" value="未设置" />
        </el-select>
        <el-button type="primary" @click="fetchData">刷新</el-button>
        <el-button type="success" :disabled="selectedIds.length === 0" @click="batchOpen">批量开卡</el-button>
        <el-button type="warning" :disabled="selectedIds.length === 0" @click="batchClose">批量关卡</el-button>
      </div>

      <el-table :data="devices" v-loading="loading" @selection-change="handleSelectionChange" stripe border>
        <el-table-column type="selection" width="55" />
        <el-table-column prop="device_id" label="设备号" sortable />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="type" label="类型" width="80" />
        <el-table-column prop="device_attribute" label="设备属性" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.device_attribute || '未设置' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner" label="归属人" width="120" />
        <el-table-column prop="borrower" label="领用人" width="100" />
        <el-table-column prop="iot_card_status" label="IoT卡状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.iot_card_status === '开卡' ? 'success' : row.iot_card_status === '关卡' ? 'danger' : 'info'">
              {{ row.iot_card_status || '未设置' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="toggleCard(row, '开卡')"
              :disabled="row.iot_card_status === '开卡'">开卡</el-button>
            <el-button size="small" type="danger" @click="toggleCard(row, '关卡')"
              :disabled="row.iot_card_status === '关卡'">关卡</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next" @current-change="fetchData"
        style="margin-top: 16px; justify-content: flex-end" />
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { inventoryAPI } from '../api/index.js';

const loading = ref(false);
const devices = ref([]);
const selectedIds = ref([]);
const filterStatus = ref('');
const page = ref(1);
const pageSize = ref(50);
const total = ref(0);

const fetchData = async () => {
  loading.value = true;
  try {
    const params = {
      version: '4G',
      skip: (page.value - 1) * pageSize.value,
      limit: pageSize.value
    };
    if (filterStatus.value === '未设置') {
      // 排除已开卡和已关卡的
    } else if (filterStatus.value) {
      params.iot_card_status = filterStatus.value;
    }
    const res = await inventoryAPI.getAll(params);
    devices.value = res.items;
    total.value = res.total;
  } catch (e) {
    ElMessage.error('获取设备列表失败');
  } finally {
    loading.value = false;
  }
};

const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(d => d.device_id);
};

const toggleCard = async (row, status) => {
  try {
    await inventoryAPI.updateIoTCard(row.device_id, status);
    ElMessage.success(`设备 ${row.device_id} IoT卡已${status}`);
    fetchData();
  } catch (e) {
    ElMessage.error(`操作失败: ${e.response?.data?.detail || e.message}`);
  }
};

const batchOpen = async () => {
  try {
    await ElMessageBox.confirm(`确认将 ${selectedIds.value.length} 台设备批量开卡？`, '批量开卡', { type: 'info' });
    await inventoryAPI.batchUpdateIoTCard(selectedIds.value, '开卡');
    ElMessage.success(`成功批量开卡 ${selectedIds.value.length} 台设备`);
    fetchData();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(`批量操作失败: ${e.response?.data?.detail || e.message}`);
  }
};

const batchClose = async () => {
  try {
    await ElMessageBox.confirm(`确认将 ${selectedIds.value.length} 台设备批量关卡？`, '批量关卡', { type: 'warning' });
    await inventoryAPI.batchUpdateIoTCard(selectedIds.value, '关卡');
    ElMessage.success(`成功批量关卡 ${selectedIds.value.length} 台设备`);
    fetchData();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(`批量操作失败: ${e.response?.data?.detail || e.message}`);
  }
};

fetchData();
</script>

<style scoped>
.iot-management { padding: 20px; }
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0; color: #303133; }
.page-header p { margin: 4px 0 0; color: #909399; font-size: 14px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; }
</style>
