<template>
  <div id="app">
    <!-- Login Page -->
    <Login v-if="!isLoggedIn" @login-success="onLoginSuccess" />

    <!-- Main App -->
    <el-container v-else>
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
          <el-menu-item index="inventory">
            <el-icon><Grid /></el-icon>
            <span>设备列表</span>
          </el-menu-item>
          <el-menu-item index="borrow">
            <el-icon><DocumentChecked /></el-icon>
            <span>借用管理</span>
          </el-menu-item>
          <el-menu-item index="iot-management">
            <el-icon><Connection /></el-icon>
            <span>IoT卡管理</span>
          </el-menu-item>
          <el-menu-item index="ai-assistant">
            <el-icon><ChatLineRound /></el-icon>
            <span>AI助手</span>
          </el-menu-item>
          <el-menu-item index="reminders">
            <el-icon><Bell /></el-icon>
            <span>提醒中心</span>
          </el-menu-item>
          <el-menu-item index="analytics">
            <el-icon><DataAnalysis /></el-icon>
            <span>统计分析</span>
          </el-menu-item>
          <el-menu-item index="operation-logs">
            <el-icon><Document /></el-icon>
            <span>操作日志</span>
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
                    <el-dropdown-item command="logout">退出登录</el-dropdown-item>
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
          <OperationLogs v-if="activeMenu === 'operation-logs'" />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import { Monitor, Grid, ChatLineRound, Bell, DataAnalysis, DocumentChecked, Connection, Document, ArrowDown } from '@element-plus/icons-vue';
import Login from './components/Login.vue';
import Dashboard from './components/Dashboard.vue';
import Inventory from './components/Inventory.vue';
import BorrowManagement from './components/BorrowManagement.vue';
import IoTManagement from './components/IoTManagement.vue';
import AIAssistant from './components/AIAssistant.vue';
import Reminders from './components/Reminders.vue';
import Analytics from './components/Analytics.vue';
import OperationLogs from './components/OperationLogs.vue';

export default {
  name: 'App',
  components: {
    Login,
    Dashboard,
    Inventory,
    BorrowManagement,
    IoTManagement,
    AIAssistant,
    Reminders,
    Analytics,
    OperationLogs,
    Monitor, Grid, ChatLineRound, Bell, DataAnalysis,
    DocumentChecked, Connection, Document, ArrowDown
  },
  setup() {
    const isLoggedIn = ref(!!localStorage.getItem('access_token'));
    const activeMenu = ref('dashboard');
    const refreshKey = ref(0); // 用于触发子组件刷新

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

    const onLoginSuccess = () => {
      isLoggedIn.value = true;
      userInfo.value = JSON.parse(localStorage.getItem('user_info') || '{}');
    };

    const handleMenuSelect = (index) => {
      activeMenu.value = index;
    };

    const handleUserCommand = (command) => {
      if (command === 'logout') {
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
        'iot-management': 'IoT卡管理',
        'ai-assistant': 'AI助手',
        'reminders': '提醒中心',
        'analytics': '统计分析',
        'operation-logs': '操作日志'
      };
      return titles[activeMenu.value] || '仪表板';
    });

    return {
      isLoggedIn, activeMenu, userName, roleText, refreshKey,
      onLoginSuccess, handleMenuSelect, handleUserCommand, getPageTitle
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
