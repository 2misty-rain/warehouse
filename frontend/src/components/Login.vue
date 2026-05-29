<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>智能库存管理系统</h1>
        <p>请登录以继续</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码"
            show-password size="large" @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="handleLogin" style="width: 100%">
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>
      <p class="login-link">
        没有账号？<a href="#" @click.prevent="$emit('go-register')">立即注册</a>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { ElMessage } from 'element-plus';
import { authAPI } from '../api/index.js';

const emit = defineEmits(['login-success', 'go-register']);
const formRef = ref(null);
const loading = ref(false);

const form = reactive({
  username: '',
  password: ''
});

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
};

const handleLogin = async () => {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    const res = await authAPI.login(form);
    localStorage.setItem('access_token', res.access_token);
    localStorage.setItem('user_info', JSON.stringify({
      username: res.username,
      role: res.role
    }));
    ElMessage.success(`欢迎回来，${res.username}！`);
    emit('login-success');
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.login-header {
  text-align: center;
  margin-bottom: 30px;
}
.login-header h1 {
  font-size: 22px;
  color: #303133;
  margin: 0 0 8px 0;
}
.login-header p {
  color: #909399;
  margin: 0;
}
.login-link {
  text-align: center;
  color: #909399;
  font-size: 14px;
  margin-top: 16px;
}
.login-link a {
  color: #409EFF;
  text-decoration: none;
}
</style>
