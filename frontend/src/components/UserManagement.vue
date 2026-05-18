<template>
  <div class="user-management">
    <div class="header">
      <el-button type="primary" @click="showAddDialog = true">新增用户</el-button>
      <el-button @click="loadUsers">刷新</el-button>
    </div>

    <el-table :data="userList" v-loading="loading" border stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" width="150" />
      <el-table-column prop="email" label="邮箱" width="200">
        <template #default="{ row }">{{ row.email || '-' }}</template>
      </el-table-column>
      <el-table-column label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="roleType(row.role)" size="small">{{ roleText(row.role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          {{ row.created_at ? new Date(row.created_at).toLocaleString() : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="editUser(row)">编辑</el-button>
          <el-button size="small" :type="row.is_active ? 'warning' : 'success'"
            @click="toggleActive(row)">{{ row.is_active ? '禁用' : '启用' }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑用户对话框 -->
    <el-dialog :title="editingUser ? '编辑用户' : '新增用户'" v-model="showAddDialog" width="450px">
      <el-form :model="userForm" :rules="userRules" ref="userFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" :disabled="!!editingUser" placeholder="用户名" />
        </el-form-item>
        <el-form-item label="密码" :prop="editingUser ? null : 'password'">
          <el-input v-model="userForm.password" type="password" show-password
            :placeholder="editingUser ? '留空则不修改' : '请输入密码（至少6位）'" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="userForm.email" placeholder="可选" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role">
            <el-option label="管理员(admin)" value="admin" />
            <el-option label="操作员(operator)" value="operator" />
            <el-option label="观察者(viewer)" value="viewer" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitUser" :loading="saving">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, reactive } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { authAPI } from '../api';

export default {
  name: 'UserManagement',
  setup() {
    const userList = ref([]);
    const loading = ref(false);
    const saving = ref(false);
    const showAddDialog = ref(false);
    const editingUser = ref(null);
    const userFormRef = ref(null);

    const userForm = reactive({
      username: '', password: '', email: '', role: 'operator'
    });
    const userRules = {
      username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
      password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
      ]
    };

    const loadUsers = async () => {
      loading.value = true;
      try { userList.value = await authAPI.getUsers(); }
      catch { ElMessage.error('加载用户列表失败'); }
      finally { loading.value = false; }
    };

    const editUser = (row) => {
      editingUser.value = row;
      userForm.username = row.username;
      userForm.password = '';
      userForm.email = row.email || '';
      userForm.role = row.role;
      showAddDialog.value = true;
    };

    const submitUser = async () => {
      const valid = await userFormRef.value.validate().catch(() => false);
      if (!valid) return;
      saving.value = true;
      try {
        if (editingUser.value) {
          const data = { email: userForm.email, role: userForm.role };
          if (userForm.password) data.password = userForm.password;
          await authAPI.updateUser(editingUser.value.id, data);
          ElMessage.success('用户已更新');
        } else {
          await authAPI.register({
            username: userForm.username,
            password: userForm.password,
            email: userForm.email,
            role: userForm.role
          });
          ElMessage.success('用户已创建');
        }
        showAddDialog.value = false;
        editingUser.value = null;
        userForm.username = ''; userForm.password = ''; userForm.email = ''; userForm.role = 'operator';
        loadUsers();
      } catch (e) {
        ElMessage.error(e.response?.data?.detail || '操作失败');
      } finally { saving.value = false; }
    };

    const toggleActive = async (row) => {
      try {
        await ElMessageBox.confirm(
          `确定要${row.is_active ? '禁用' : '启用'}用户 ${row.username} 吗？`,
          `${row.is_active ? '禁用' : '启用'}用户`,
          { type: 'warning' }
        );
        await authAPI.updateUser(row.id, { is_active: !row.is_active });
        ElMessage.success(`用户已${row.is_active ? '禁用' : '启用'}`);
        loadUsers();
      } catch (e) {
        if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败');
      }
    };

    const roleType = (r) => ({ admin: '', operator: 'warning', viewer: 'info' }[r] || 'info');
    const roleText = (r) => ({ admin: '管理员', operator: '操作员', viewer: '观察者' }[r] || r);

    onMounted(() => { loadUsers(); });

    return {
      userList, loading, saving, showAddDialog, editingUser,
      userForm, userRules, userFormRef,
      loadUsers, editUser, submitUser, toggleActive,
      roleType, roleText
    };
  }
};
</script>

<style scoped>
.user-management { padding: 20px; }
.header { margin-bottom: 20px; }
</style>
