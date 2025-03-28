<template>
    <el-dialog v-model="authDialogVisible" title="账号授权" width="500px" :close-on-click-modal="false">
      <el-form :model="form" :rules="rules" ref="authForm" label-width="80px">
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" disabled style="width: 250px" />
        </el-form-item>
  
        <el-form-item label="验证码" prop="authCode">
          <div style="display: flex; align-items: center; gap: 10px">
            <el-input v-model="form.authCode" placeholder="请输入验证码" style="width: 200px" />
            <el-button type="primary" @click="sendAuthCode" :disabled="isCodeSent">
              {{ isCodeSent ? `${countdown}s 后重试` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
  
      <template #footer>
        <el-button @click="authDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAuth">确认授权</el-button>
      </template>
    </el-dialog>
  </template>
  
  <script setup>
  import { ref, reactive, onUnmounted } from 'vue';
  import { ElMessage } from 'element-plus';
  
  // 后端地址（统一配置）
  const API_BASE_URL = 'http://192.168.6.188:59006';
  
  // 弹窗显示状态
  const authDialogVisible = ref(false);
  
  // 表单数据
  const form = reactive({
    phone: '',
    authCode: '', // 将 authCode 放入 form 中，与表单校验绑定
  });
  
  // 验证码发送状态和倒计时
  const isCodeSent = ref(false);
  const countdown = ref(60);
  let countdownTimer = null;
  const phoneCodeHash = ref('');
  
  // 表单引用和校验规则
  const authForm = ref(null);
  const rules = {
    authCode: [
      { required: true, message: '请输入验证码', trigger: 'change' }, // 修改 trigger 为 change
      { min: 5, max: 6, message: '验证码长度为 5-6 位', trigger: 'change' },
    ],
  };
  
  // 发送验证码
  const sendAuthCode = async () => {
    if (!form.phone) {
      ElMessage.error('手机号不能为空');
      return;
    }
  
    try {
      const response = await fetch(`${API_BASE_URL}/request_code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: form.phone }),
      });
      const result = await response.json();
  
      if (result.status === 'pending') {
        ElMessage.success(result.message);
        phoneCodeHash.value = result.phone_code_hash;
        startCountdown();
      } else if (result.status === 'success') {
        ElMessage.info(result.message);
        authDialogVisible.value = false;
        emit('auth-success');
      } else {
        ElMessage.error(result.message);
      }
    } catch (error) {
      ElMessage.error(`请求失败: ${error.message}`);
    }
  };
  
  // 开始倒计时
  const startCountdown = () => {
    isCodeSent.value = true;
    countdown.value = 60;
  
    countdownTimer = setInterval(() => {
      countdown.value--;
      if (countdown.value <= 0) {
        clearInterval(countdownTimer);
        isCodeSent.value = false;
      }
    }, 1000);
  };
  
  // 确认授权
  const confirmAuth = () => {
    console.log('authCode:', form.authCode); // 调试：打印验证码
    authForm.value.validate(async (valid) => {
      if (valid) {
        try {
          const response = await fetch(`${API_BASE_URL}/verify_code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              phone: form.phone,
              code: form.authCode,
              phone_code_hash: phoneCodeHash.value
            }),
          });
          const result = await response.json();
  
          if (result.status === 'success') {
            ElMessage.success(result.message);
            authDialogVisible.value = false;
            form.authCode = ''; // 清空验证码
            emit('auth-success');
          } else {
            ElMessage.error(result.message);
          }
        } catch (error) {
          ElMessage.error(`验证失败: ${error.message}`);
        }
      } else {
        ElMessage.warning('请填写正确的验证码');
      }
    });
  };
  
  // 定义事件
  const emit = defineEmits(['auth-success']);
  
  // 清理倒计时
  onUnmounted(() => {
    if (countdownTimer) {
      clearInterval(countdownTimer);
    }
  });
  
  // 暴露方法给外部调用
  defineExpose({
    openAuthDialog(phone) {
      form.phone = phone;
      form.authCode = ''; // 重置验证码
      authDialogVisible.value = true;
    },
  });
  </script>
  
  <style scoped>
  .el-form-item {
    margin-bottom: 20px;
  }
  </style>