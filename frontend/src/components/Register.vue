<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h1>账号注册</h1>
        <p>注册后请联系管理员激活账号</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码（至少6位）"
            show-password size="large" @keyup.enter="handleRegister" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码"
            show-password size="large" @keyup.enter="handleRegister" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="handleRegister" style="width: 100%">
            {{ loading ? '注册中...' : '注 册' }}
          </el-button>
        </el-form-item>
      </el-form>
      <p class="login-link">
        已有账号？<a href="#" @click.prevent="$emit('go-login')">返回登录</a>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { ElMessage } from 'element-plus';
import { authAPI } from '../api/index.js';

const emit = defineEmits(['go-login']);
const formRef = ref(null);
const loading = ref(false);

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
});

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'));
        } else {
          callback();
        }
      },
      trigger: 'blur'
    }
  ]
};

const handleRegister = async () => {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await authAPI.register({ username: form.username, password: form.password });
    ElMessage.success('注册成功，请登录');
    emit('go-login');
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.register-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.register-header {
  text-align: center;
  margin-bottom: 30px;
}
.register-header h1 {
  font-size: 22px;
  color: #303133;
  margin: 0 0 8px 0;
}
.register-header p {
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
