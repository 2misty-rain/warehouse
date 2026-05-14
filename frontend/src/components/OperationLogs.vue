<template>
  <div class="operation-logs">
    <div class="page-header">
      <h2>操作日志</h2>
      <p>系统所有操作的审计记录</p>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-select v-model="filterType" placeholder="操作类型" clearable @change="fetchData">
          <el-option label="创建" value="create" />
          <el-option label="更新" value="update" />
          <el-option label="删除" value="delete" />
          <el-option label="借出" value="borrow" />
          <el-option label="归还" value="return" />
          <el-option label="销售" value="sell" />
          <el-option label="导入" value="import" />
        </el-select>
        <el-input v-model="filterUser" placeholder="操作人" clearable style="width: 200px" @change="fetchData" />
        <el-button type="primary" @click="fetchData">查询</el-button>
      </div>

      <el-table :data="logs" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="操作人" width="100" />
        <el-table-column prop="operation_type" label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag :type="typeColor(row.operation_type)" size="small">{{ row.operation_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="device_id" label="目标设备" width="150" />
        <el-table-column prop="details" label="详情" min-width="250">
          <template #default="{ row }">
            <span style="font-size: 13px; color: #606266">{{ formatDetails(row.details) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="操作时间" width="180" />
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
import { ElMessage } from 'element-plus';
import { operationLogAPI } from '../api/index.js';

const loading = ref(false);
const logs = ref([]);
const filterType = ref('');
const filterUser = ref('');
const page = ref(1);
const pageSize = ref(50);
const total = ref(0);

const fetchData = async () => {
  loading.value = true;
  try {
    const params = {
      skip: (page.value - 1) * pageSize.value,
      limit: pageSize.value
    };
    if (filterType.value) params.operation_type = filterType.value;
    if (filterUser.value) params.username = filterUser.value;

    const data = await operationLogAPI.getList(params);
    logs.value = data.items || [];
    total.value = data.total || 0;
  } catch (e) {
    ElMessage.error('获取操作日志失败');
  } finally {
    loading.value = false;
  }
};

const typeColor = (type) => {
  const map = {
    create: 'success', update: 'warning', delete: 'danger',
    borrow: '', return: 'success', sell: 'danger', import: 'info'
  };
  return map[type] || 'info';
};

const formatDetails = (details) => {
  try {
    const obj = JSON.parse(details);
    return JSON.stringify(obj, null, 2);
  } catch {
    return details || '-';
  }
};

fetchData();
</script>

<style scoped>
.operation-logs { padding: 20px; }
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0; color: #303133; }
.page-header p { margin: 4px 0 0; color: #909399; font-size: 14px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; }
</style>
