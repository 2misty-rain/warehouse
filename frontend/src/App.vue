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
      <el-aside width="220px" class="sidebar">
        <div class="logo">
          <h3>Life Radar</h3>
          <p>智能运营管理平台</p>
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

          <el-sub-menu index="inventory-sub" v-if="canAccessInventory">
            <template #title>
              <el-icon><Box /></el-icon>
              <span>库存系统</span>
            </template>
            <el-menu-item index="inventory">
              <el-icon><Grid /></el-icon>
              <span>设备列表</span>
            </el-menu-item>
            <el-menu-item index="borrow">
              <el-icon><DocumentChecked /></el-icon>
              <span>借用管理</span>
            </el-menu-item>
            <el-menu-item index="reservation">
              <el-icon><Tickets /></el-icon>
              <span>出库预约</span>
            </el-menu-item>
            <el-menu-item index="iot-management">
              <el-icon><Connection /></el-icon>
              <span>IoT卡管理</span>
            </el-menu-item>
            <el-menu-item index="reminders">
              <el-icon><Bell /></el-icon>
              <span>提醒中心</span>
            </el-menu-item>
            <el-menu-item index="analytics">
              <el-icon><DataAnalysis /></el-icon>
              <span>统计分析</span>
            </el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="ops-sub" v-if="canAccessInventory">
            <template #title>
              <el-icon><Monitor /></el-icon>
              <span>运营平台</span>
            </template>
            <el-menu-item index="device-monitor">
              <el-icon><Connection /></el-icon>
              <span>设备监控</span>
            </el-menu-item>
            <el-menu-item index="anomaly-tickets">
              <el-icon><Warning /></el-icon>
              <span>异常工单</span>
            </el-menu-item>
            <el-menu-item index="ops-reports">
              <el-icon><Document /></el-icon>
              <span>数据报告</span>
            </el-menu-item>
          </el-sub-menu>

          <el-menu-item index="ai-assistant" v-if="isAdmin">
            <el-icon><ChatLineRound /></el-icon>
            <span>AI助手</span>
          </el-menu-item>

          <el-menu-item index="toolbox">
            <el-icon><Switch /></el-icon>
            <span>工具箱</span>
          </el-menu-item>

          <el-sub-menu index="system-sub" v-if="isAdmin">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item index="operation-logs">
              <el-icon><Document /></el-icon>
              <span>操作日志</span>
            </el-menu-item>
            <el-menu-item index="user-management">
              <el-icon><User /></el-icon>
              <span>账号管理</span>
            </el-menu-item>
          </el-sub-menu>
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
          <Reminders v-if="activeMenu === 'reminders'" />
          <Analytics v-if="activeMenu === 'analytics'" />
          <ReservationManagement v-if="activeMenu === 'reservation'" />
          <DailyOps v-if="activeMenu === 'daily-ops'" />
          <DeviceMonitor v-if="activeMenu === 'device-monitor'" />
          <AnomalyTickets v-if="activeMenu === 'anomaly-tickets'" />
          <OpsReports v-if="activeMenu === 'ops-reports'" />
          <AIAssistant v-if="activeMenu === 'ai-assistant'" />
          <OperationLogs v-if="activeMenu === 'operation-logs'" />
          <UserManagement v-if="activeMenu === 'user-management'" />
          <Toolbox v-if="activeMenu === 'toolbox'" />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script>
import { ref, reactive, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { Monitor, Grid, ChatLineRound, Bell, DataAnalysis, DocumentChecked, Connection, Document, ArrowDown, Tickets, Setting, TrendCharts, Box, Warning, User, Switch } from '@element-plus/icons-vue';
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
import DailyOps from './components/DailyOps.vue';
import DeviceMonitor from './components/DeviceMonitor.vue';
import AnomalyTickets from './components/AnomalyTickets.vue';
import OpsReports from './components/OpsReports.vue';
import Toolbox from './components/Toolbox.vue';

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
    DailyOps,
    DeviceMonitor,
    AnomalyTickets,
    OpsReports,
    Toolbox,
    Monitor, Grid, ChatLineRound, Bell, DataAnalysis,
    DocumentChecked, Connection, Document, ArrowDown, Tickets, Setting, TrendCharts,
    Box, Warning, User, Switch
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
        'daily-ops': '每日运维',
        'device-monitor': '设备监控',
        'anomaly-tickets': '异常工单',
        'ops-reports': '数据报告',
        'operation-logs': '操作日志',
        'user-management': '账号管理',
        'toolbox': '工具箱'
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
#app { height: 100vh; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; }

/* === Sidebar === */
.sidebar {
  background: #2d3348;
  height: 100vh; position: fixed; top: 0; left: 0; z-index: 100; overflow-y: auto;
  width: 220px;
}
.el-container { padding-left: 220px; }

.logo {
  color: white; text-align: center; padding: 24px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.logo h3 {
  margin: 0; font-size: 17px; font-weight: 700; color: #ffffff;
  letter-spacing: 1px;
}
.logo p { margin: 4px 0 0; font-size: 11px; color: rgba(255,255,255,0.55); }

.menu { border: none; background: transparent; }
.menu .el-menu-item,
.menu .el-sub-menu__title {
  color: #bcc3d0;
  height: 44px; line-height: 44px;
  font-size: 13px;
  margin: 2px 8px; border-radius: 8px;
  transition: all 0.2s;
}
.menu .el-menu-item:hover,
.menu .el-sub-menu__title:hover {
  background-color: rgba(255,255,255,0.1);
  color: #e8ebf0;
}
.menu .el-menu-item.is-active {
  background: #1a73e8;
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(26,115,232,0.3);
}
.menu .el-sub-menu .el-menu-item { padding-left: 56px !important; }

/* === Header === */
.header {
  background: #ffffff;
  box-shadow: 0 1px 0 rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.04);
  padding: 0 24px; height: 56px;
  position: sticky; top: 0; z-index: 50;
}
.header-content { display: flex; justify-content: space-between; align-items: center; height: 100%; }
.header h1 { margin: 0; font-size: 16px; font-weight: 600; color: #1a1f36; }
.user-info { display: flex; align-items: center; }
.el-dropdown-link {
  cursor: pointer; color: #1a73e8; display: flex; align-items: center;
  gap: 6px; font-size: 13px; font-weight: 500;
}

/* === Main Content === */
.main-content {
  margin-top: 0; padding: 20px 24px 24px 24px;
  background-color: #f0f2f5; min-height: calc(100vh - 56px);
}

/* === Global card styles === */
.el-card {
  border-radius: 12px !important;
  border: 1px solid rgba(0,0,0,0.04) !important;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
  transition: box-shadow 0.3s;
}
.el-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important; }
.el-card__header {
  padding: 14px 20px !important;
  border-bottom: 1px solid #f0f0f0 !important;
  font-weight: 600; font-size: 14px;
}
.el-card__body { padding: 20px !important; }

/* === Global table styles === */
.el-table { border-radius: 8px; overflow: hidden; }
.el-table th.el-table__cell {
  background: #f7f8fa !important;
  color: #5a5f6b; font-weight: 600; font-size: 12px;
  height: 44px;
}
.el-table .el-table__row { height: 48px; }
.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background: #fafbfc;
}

/* === Global tag styles === */
.el-tag {
  border-radius: 20px; padding: 0 10px; height: 24px; line-height: 22px;
  font-size: 11px; font-weight: 500;
}

/* === Global button styles === */
.el-button { border-radius: 8px; font-weight: 500; }
.el-button--primary {
  background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%);
  border: none;
}
.el-button--primary:hover {
  background: linear-gradient(135deg, #1d7ff0 0%, #1861c0 100%);
}

/* === Global dialog styles === */
.el-dialog { border-radius: 16px; overflow: hidden; }
.el-dialog__header { padding: 20px 24px 16px; border-bottom: 1px solid #f0f0f0; }
.el-dialog__body { padding: 24px; }
.el-dialog__footer { padding: 12px 24px 20px; }

/* === Stat cards (used in dashboard + ops pages) === */
.stat-card {
  text-align: center; cursor: default;
  position: relative; overflow: hidden;
}
.stat-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0;
  height: 4px;
}
.stat-card.green::before { background: linear-gradient(90deg, #52c41a, #73d13d); }
.stat-card.blue::before { background: linear-gradient(90deg, #1a73e8, #4dabf7); }
.stat-card.orange::before { background: linear-gradient(90deg, #fa8c16, #ffc069); }
.stat-card.red::before { background: linear-gradient(90deg, #f5222d, #ff7875); }
.stat-value { font-size: 30px; font-weight: 700; margin: 4px 0; }
.stat-label { font-size: 12px; color: #8c8c8c; margin-top: 4px; }

/* scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d9d9d9; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #bfbfbf; }
</style>
