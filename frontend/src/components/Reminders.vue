<template>
  <div class="reminders">
    <div class="header">
      <el-button type="primary" @click="showAddDialog = true">添加提醒</el-button>
      <el-button @click="loadReminders">刷新</el-button>
    </div>

    <el-table 
      :data="reminders" 
      v-loading="loading"
      style="width: 100%" 
      border
      stripe
    >
      <el-table-column prop="device_id" label="设备号" width="150"></el-table-column>
      <el-table-column prop="reminder_type" label="提醒类型" width="120">
        <template #default="{ row }">
          <el-tag 
            :type="getReminderTypeTag(row.reminder_type)"
            size="small"
          >
            {{ getReminderTypeName(row.reminder_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="due_date" label="到期日期" width="120">
        <template #default="{ row }">
          {{ row.due_date ? new Date(row.due_date).toLocaleDateString() : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述"></el-table-column>
      <el-table-column prop="is_processed" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_processed ? 'success' : 'warning'">
            {{ row.is_processed ? '已处理' : '未处理' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button 
            size="small" 
            @click="toggleReminderStatus(row.id, !row.is_processed)"
            :type="row.is_processed ? 'info' : 'primary'"
          >
            {{ row.is_processed ? '重新打开' : '标记完成' }}
          </el-button>
          <el-button size="small" type="danger" @click="deleteReminder(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加提醒对话框 -->
    <el-dialog
      title="添加提醒"
      v-model="showAddDialog"
      width="50%"
    >
      <el-form :model="newReminder" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="设备号" prop="device_id">
          <el-input v-model="newReminder.device_id" placeholder="例如：CAA241100458"></el-input>
        </el-form-item>
        <el-form-item label="提醒类型" prop="reminder_type">
          <el-select v-model="newReminder.reminder_type" placeholder="请选择提醒类型">
            <el-option label="试用期" value="trial_period"></el-option>
            <el-option label="物联网卡" value="iot_card"></el-option>
            <el-option label="其他" value="other"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="到期日期" prop="due_date">
          <el-date-picker
            v-model="newReminder.due_date"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD">
          </el-date-picker>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="newReminder.description" type="textarea"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="primary" @click="createReminder">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { reminderAPI } from '../api';
import { ElMessage, ElMessageBox } from 'element-plus';

export default {
  name: 'Reminders',
  setup() {
    const reminders = ref([]);
    const loading = ref(false);
    const showAddDialog = ref(false);
    
    const newReminder = ref({
      device_id: '',
      reminder_type: 'other',
      due_date: null,
      description: ''
    });
    
    const rules = {
      device_id: [{ required: true, message: '请输入设备号', trigger: 'blur' }],
      reminder_type: [{ required: true, message: '请选择提醒类型', trigger: 'change' }],
      due_date: [{ required: true, message: '请选择到期日期', trigger: 'change' }]
    };
    
    const formRef = ref(null);

    const loadReminders = async () => {
      loading.value = true;
      try {
        const response = await reminderAPI.getAll();
        reminders.value = response;
      } catch (error) {
        console.error('加载提醒列表失败:', error);
        ElMessage.error('加载提醒列表失败');
      } finally {
        loading.value = false;
      }
    };

    const getReminderTypeName = (type) => {
      const types = {
        'trial_period': '试用期',
        'iot_card': '物联网卡',
        'other': '其他'
      };
      return types[type] || type;
    };

    const getReminderTypeTag = (type) => {
      const tags = {
        'trial_period': 'warning',
        'iot_card': 'danger',
        'other': 'info'
      };
      return tags[type] || 'info';
    };

    const toggleReminderStatus = async (id, status) => {
      try {
        await reminderAPI.update(id, status);
        ElMessage.success(status ? '提醒标记为已完成' : '提醒重新打开');
        loadReminders(); // 重新加载列表
      } catch (error) {
        console.error('更新提醒状态失败:', error);
        ElMessage.error('更新提醒状态失败');
      }
    };

    const deleteReminder = async (id) => {
      try {
        await ElMessageBox.confirm(
          '确定要删除这个提醒吗？',
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        await reminderAPI.delete(id);
        ElMessage.success('提醒删除成功');
        loadReminders(); // 重新加载列表
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除提醒失败:', error);
          ElMessage.error('删除提醒失败');
        }
      }
    };

    const createReminder = async () => {
      try {
        await reminderAPI.create(newReminder.value);
        ElMessage.success('提醒创建成功');
        showAddDialog.value = false;
        resetForm();
        loadReminders(); // 重新加载列表
      } catch (error) {
        console.error('创建提醒失败:', error);
        ElMessage.error('创建提醒失败');
      }
    };

    const resetForm = () => {
      Object.keys(newReminder.value).forEach(key => {
        if (key === 'due_date') {
          newReminder.value[key] = null;
        } else {
          newReminder.value[key] = '';
        }
      });
    };

    onMounted(() => {
      loadReminders();
    });

    return {
      reminders,
      loading,
      showAddDialog,
      newReminder,
      rules,
      formRef,
      loadReminders,
      getReminderTypeName,
      getReminderTypeTag,
      toggleReminderStatus,
      deleteReminder,
      createReminder
    };
  }
};
</script>

<style scoped>
.reminders {
  padding: 20px;
}

.header {
  margin-bottom: 20px;
}

.dialog-footer {
  text-align: right;
}
</style>