<template>
  <div id="app">
    <!-- Login Page -->
    <Login v-if="!isLoggedIn && !showRegister" @login-success="onLoginSuccess" @go-register="showRegister = true" />
    <!-- Register Page -->
    <Register v-else-if="!isLoggedIn && showRegister" @go-login="showRegister = false" />
    <!-- Main App -->
    <el-container v-else>
      <!-- Change Password Dialog -->
      <el-dialog v-model="showPasswordDialog" title="修改密码" width="400px" append-to-body>
        <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="100px">
          <el-form-item label="当前密码" prop="currentPassword">
            <el-input v-model="passwordForm.currentPassword" type="password" show-password placeholder="请输入当前密码" />
          </el-form-item>
          <el-form-item label="新密码" prop="newPassword">
            <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="请输入新密码（至少6位）" />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirmPassword">
            <el-input v-model="passwordForm.confirmPassword" type="password" show-password placeholder="请再次输入新密码" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showPasswordDialog = false">取消</el-button>
          <el-button type="primary" @click="submitChangePassword" :loading="changingPassword">确定</el-button>
        </template>
      </el-dialog>
      <el-aside width="200px" class="sidebar">
        <div class="logo">
          <h3>库存系统</h3>
        </div>
        <el-menu
          :default-active="activeMenu"
          class="menu"
          @select="handleMenuSelect"
          :unique-opened="true"
          :router="false"
        >
          <el-menu-item index="dashboard">
            <el-icon><Monitor /></el-icon>
            <span>仪表板</span>
          </el-menu-item>
          <el-menu-item index="inventory" v-if="canAccessInventory">
            <el-icon><Grid /></el-icon>
            <span>设备列表</span>
          </el-menu-item>
          <el-menu-item index="borrow" v-if="canAccessInventory">
            <el-icon><DocumentChecked /></el-icon>
            <span>借用管理</span>
          </el-menu-item>
          <el-menu-item index="reservation">
            <el-icon><Tickets /></el-icon>
            <span>出库预约</span>
          </el-menu-item>
          <el-menu-item index="iot-management" v-if="canAccessInventory">
            <el-icon><Connection /></el-icon>
            <span>IoT卡管理</span>
          </el-menu-item>
          <el-menu-item index="ai-assistant" v-if="isAdmin">
            <el-icon><ChatLineRound /></el-icon>
            <span>AI助手</span>
          </el-menu-item>
          <el-menu-item index="reminders" v-if="canAccessInventory">
            <el-icon><Bell /></el-icon>
            <span>提醒中心</span>
          </el-menu-item>
          <el-menu-item index="analytics" v-if="canAccessInventory">
            <el-icon><DataAnalysis /></el-icon>
            <span>统计分析</span>
          </el-menu-item>
          <el-menu-item index="operation-logs" v-if="isAdmin">
            <el-icon><Document /></el-icon>
            <span>操作日志</span>
          </el-menu-item>
          <el-menu-item index="user-management" v-if="isAdmin">
            <el-icon><Setting /></el-icon>
            <span>账号管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header class="header">
          <div class="header-content">
            <h1>{{ getPageTitle }}</h1>
            <div class="user-info">
              <el-dropdown @command="handleUserCommand">
                <span class="el-dropdown-link">
                  {{ userName }} ({{ roleText }})<el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="changePassword">修改密码</el-dropdown-item>
                    <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </el-header>

        <el-main class="main-content" :key="refreshKey">
          <Dashboard v-if="activeMenu === 'dashboard'" />
          <Inventory v-if="activeMenu === 'inventory'" />
          <BorrowManagement v-if="activeMenu === 'borrow'" />
          <IoTManagement v-if="activeMenu === 'iot-management'" />
          <AIAssistant v-if="activeMenu === 'ai-assistant'" />
          <Reminders v-if="activeMenu === 'reminders'" />
          <Analytics v-if="activeMenu === 'analytics'" />
          <ReservationManagement v-if="activeMenu === 'reservation'" />
          <OperationLogs v-if="activeMenu === 'operation-logs'" />
          <UserManagement v-if="activeMenu === 'user-management'" />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script>
import { ref, reactive, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { Monitor, Grid, ChatLineRound, Bell, DataAnalysis, DocumentChecked, Connection, Document, ArrowDown, Tickets, Setting } from '@element-plus/icons-vue';
import Login from './components/Login.vue';
import Register from './components/Register.vue';
import Dashboard from './components/Dashboard.vue';
import Inventory from './components/Inventory.vue';
import BorrowManagement from './components/BorrowManagement.vue';
import IoTManagement from './components/IoTManagement.vue';
import AIAssistant from './components/AIAssistant.vue';
import ReservationManagement from './components/ReservationManagement.vue';
import Reminders from './components/Reminders.vue';
import Analytics from './components/Analytics.vue';
import OperationLogs from './components/OperationLogs.vue';
import UserManagement from './components/UserManagement.vue';

export default {
  name: 'App',
  components: {
    Login, Register,
    Dashboard,
    Inventory,
    BorrowManagement,
    IoTManagement,
    AIAssistant,
    ReservationManagement,
    Reminders,
    Analytics,
    OperationLogs,
    UserManagement,
    Monitor, Grid, ChatLineRound, Bell, DataAnalysis,
    DocumentChecked, Connection, Document, ArrowDown, Tickets, Setting
  },
  setup() {
    const isLoggedIn = ref(!!localStorage.getItem('access_token'));
    const showRegister = ref(false);
    const activeMenu = ref('dashboard');
    const refreshKey = ref(0);

    const userInfo = ref(JSON.parse(localStorage.getItem('user_info') || '{}'));

    // 监听 AI 数据变更事件，触发子组件刷新
    if (typeof window !== 'undefined') {
      window.addEventListener('ai-data-changed', () => {
        refreshKey.value++;
      });
    }

    // 验证 token 有效性
    if (isLoggedIn.value) {
      import('./api/index.js').then(({ authAPI }) => {
        authAPI.getMe().catch(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user_info');
          isLoggedIn.value = false;
        });
      });
    }

    const userName = computed(() => userInfo.value.username || '管理员');
    const roleText = computed(() => {
      const map = { admin: '管理员', operator: '操作员', viewer: '观察者' };
      return map[userInfo.value.role] || '管理员';
    });
    const isAdmin = computed(() => userInfo.value.role === 'admin');
    const canAccessInventory = computed(() =>
      userInfo.value.role === 'admin' || userInfo.value.role === 'viewer'
    );

    const onLoginSuccess = () => {
      isLoggedIn.value = true;
      userInfo.value = JSON.parse(localStorage.getItem('user_info') || '{}');
    };

    const handleMenuSelect = (index) => {
      activeMenu.value = index;
    };

    // 修改密码
    const showPasswordDialog = ref(false);
    const changingPassword = ref(false);
    const passwordFormRef = ref(null);
    const passwordForm = reactive({
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    });
    const passwordRules = {
      currentPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
      newPassword: [
        { required: true, message: '请输入新密码', trigger: 'blur' },
        { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
      ],
      confirmPassword: [
        { required: true, message: '请确认新密码', trigger: 'blur' },
        {
          validator: (rule, value, callback) => {
            if (value !== passwordForm.newPassword) {
              callback(new Error('两次输入的密码不一致'));
            } else {
              callback();
            }
          },
          trigger: 'blur'
        }
      ]
    };

    const submitChangePassword = async () => {
      const valid = await passwordFormRef.value.validate().catch(() => false);
      if (!valid) return;
      changingPassword.value = true;
      try {
        const { authAPI } = await import('./api/index.js');
        await authAPI.changePassword({
          current_password: passwordForm.currentPassword,
          new_password: passwordForm.newPassword
        });
        ElMessage.success('密码修改成功');
        showPasswordDialog.value = false;
        passwordForm.currentPassword = '';
        passwordForm.newPassword = '';
        passwordForm.confirmPassword = '';
      } catch (e) {
        ElMessage.error(e.response?.data?.detail || '密码修改失败');
      } finally {
        changingPassword.value = false;
      }
    };

    const handleUserCommand = (command) => {
      if (command === 'changePassword') {
        showPasswordDialog.value = true;
      } else if (command === 'logout') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
        isLoggedIn.value = false;
      }
    };

    const getPageTitle = computed(() => {
      const titles = {
        'dashboard': '仪表板',
        'inventory': '设备列表',
        'borrow': '借用管理',
        'reservation': '出库预约',
        'iot-management': 'IoT卡管理',
        'ai-assistant': 'AI助手',
        'reminders': '提醒中心',
        'analytics': '统计分析',
        'operation-logs': '操作日志',
        'user-management': '账号管理'
      };
      return titles[activeMenu.value] || '仪表板';
    });

    return {
      isLoggedIn, showRegister, activeMenu, userName, roleText, isAdmin,
      canAccessInventory, refreshKey,
      onLoginSuccess, handleMenuSelect, handleUserCommand, getPageTitle,
      showPasswordDialog, passwordForm, passwordRules, passwordFormRef,
      changingPassword, submitChangePassword
    };
  }
};
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
#app { height: 100vh; font-family: Avenir, Helvetica, Arial, sans-serif; }
.sidebar { background-color: #545c64; height: 100vh; position: fixed; top: 0; left: 0; z-index: 100; overflow-y: auto; }
.el-container { padding-left: 200px; }
.logo { color: white; text-align: center; padding: 20px 0; border-bottom: 1px solid #444a51; }
.logo h3 { margin: 0; font-size: 18px; color: #ffffff; }
.menu { border: none; background-color: #545c64; }
.menu .el-menu-item { color: #bfcbd9; }
.menu .el-menu-item:hover { background-color: #444a51; color: #ffffff; }
.menu .el-menu-item.is-active { background-color: #409EFF; color: #ffffff; }
.header { background-color: #ffffff; box-shadow: 0 1px 4px rgba(0,21,41,.08); padding: 0 20px; height: 60px; }
.header-content { display: flex; justify-content: space-between; align-items: center; height: 100%; }
.header h1 { margin: 0; font-size: 18px; color: #303133; }
.user-info { display: flex; align-items: center; }
.el-dropdown-link { cursor: pointer; color: #409EFF; display: flex; align-items: center; gap: 4px; }
.main-content { margin-top: 20px; padding: 0 20px 20px 20px; background-color: #f5f7fa; min-height: calc(100vh - 80px); }
</style>
