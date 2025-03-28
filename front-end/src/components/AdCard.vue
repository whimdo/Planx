<!-- AdCard.vue -->
<template>
  <el-card class="ad-card">
    <div class="top">群发助手</div>
    <div class="content-area">
      <el-form :model="form" ref="adForm" class="ad-form">
        <el-form-item label="手机号" prop="phone">
          <el-row :gutter="24">
            <el-col :span="20">
              <el-input
                v-model="form.phone"
                placeholder="请输入手机号（如 +123456789）"
                style="width: 100%"
              />
            </el-col>
            <el-col :span="4">
              <el-button type="primary" @click="showAuthDialog" style="width: 100px">账号授权</el-button>
            </el-col>
          </el-row>
        </el-form-item>
        <el-form-item label="群组链接" prop="groupLinks">
          <el-input v-model="form.groupLinks" placeholder="请输入群组链接（用逗号分隔）" />
        </el-form-item>
        <el-form>
          <el-row :gutter="20">
            <el-col :span="16">
              <el-form-item label="消息内容" prop="message">
                <div style="border: 1px solid #ccc">
                  <Toolbar
                    style="border-bottom: 1px solid #ccc"
                    :editor="editorRef"
                    :defaultConfig="toolbarConfig"
                    :mode="mode"
                  />
                  <Editor
                    style="height: 400px; width: 800px; overflow-y: hidden"
                    v-model="form.message"
                    :defaultConfig="editorConfig"
                    :mode="mode"
                    @onCreated="handleCreated"
                  />
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="图片" prop="image">
                <el-upload
                  ref="uploadRef"
                  :auto-upload="false"
                  :limit="1"
                  :on-change="handleFileChange"
                  :on-exceed="handleExceed"
                  accept="image/*"
                  :file-list="fileList"
                >
                  <el-button type="primary">选择图片</el-button>
                  <template #tip>
                    <div class="el-upload__tip">上传你的消息封面（如果需要），单次上传一张，重复上传会替换</div>
                  </template>
                </el-upload>
              </el-form-item>
            </el-col>
          </el-row>
      </el-form>
        <el-form-item>
          <el-popover
            class="box-item"
            title="提示"
            content="支持多种url，若是使用id(如-1001541706958)的url需要先加入群组"
            placement="top-start"
            width="200"
          >
            <template #reference>
              <el-button
                type="primary"
                @click="handleAdRequest"
                :disabled="isLoading"
                :loading="isLoading"
              >
                发送消息
              </el-button>
            </template>
          </el-popover>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
    <!-- 嵌入授权弹窗组件 -->
    <auth-dialog ref="authDialogRef" @auth-success="onAuthSuccess" />
    <!-- 嵌入结果展示弹窗组件 -->
    <mresult-dialog
      v-model="resultDialogVisible"
      :status="resultStatus"
      :message="resultMessage"
      :failed-groups="resultFailedGroups"
      :channel-groups="resultChannelGroups"
    />
  </el-card>
</template>

<script setup>
import { ref, reactive, shallowRef, onBeforeUnmount, nextTick } from 'vue';
import { ElMessage ,genFileId} from 'element-plus';
import { Editor, Toolbar } from '@wangeditor/editor-for-vue';
import AuthDialog from './AuthDialog.vue';
import MresultDialog from './MresultDialog.vue';
import '@wangeditor/editor/dist/css/style.css';

const form = reactive({
  phone: '',
  groupLinks: '',
  message: '',
  image: null, // 存储上传的图片文件
});

const isLoading = ref(false);
const adForm = ref(null);
const editorRef = shallowRef();
const authDialogRef = ref(null);
const uploadRef = ref(null); // 引用 el-upload 组件
const fileList = ref([]); // 文件列表，用于 el-upload 显示

// 结果对话框相关状态
const resultDialogVisible = ref(false);
const resultStatus = ref('success');
const resultMessage = ref('');
const resultFailedGroups = ref([]);
const resultChannelGroups = ref([]);

// 显示授权弹窗
const showAuthDialog = () => {
  if (!form.phone) {
    ElMessage.error('请先输入手机号');
    return;
  }
  authDialogRef.value.openAuthDialog(form.phone);
};

// 授权成功回调
const onAuthSuccess = () => {
  ElMessage.success('授权成功，可以发送消息');
};

// 处理文件选择
const handleFileChange = (file) => {
  form.image = file.raw; // 获取原始文件对象
  fileList.value = [{ name: file.name, url: URL.createObjectURL(file.raw) }]; // 更新文件列表
};

// 处理超过文件限制（理论上不会触发，因为 limit=1 且由 handleFileChange 控制）
const handleExceed = (files) => {
  ElMessage.warning('只能上传一张图片，新上传的图片将替换旧图片');
  uploadRef.value.clearFiles(); // 清空现有文件
  const file = files[0]; // 获取新上传的文件
  file.uid = genFileId(); // 为新文件生成唯一的 UID
  uploadRef.value.handleStart(file); // 手动添加新文件到上传队列
  form.image = file.raw; // 更新 form.image
  fileList.value = [{ name: file.name, url: URL.createObjectURL(file.raw) }]; // 更新文件列表
};

// 仅启用基础的文字格式功能
const toolbarConfig = {
  toolbarKeys: ['bold', 'italic', 'underline', 'through', 'emotion'],
};

const editorConfig = {
  placeholder: '请输入要发送的消息内容...',
  MENU_CONF: {
    emoticon: {
      title: '表情',
      data: '😀 😃 😄 😁 😆 😅 😂 🤣 😊 😇 🙂 🙃 😉 😍 😘 😜 🤔 🤩 🤗 🤨 😎 🤯 🥳 🥺 😤 🤥 🤢 🤮 🤑'.split(' '),
    },
  },
};

const mode = 'default';

// 编辑器创建时的回调
const handleCreated = (editor) => {
  editorRef.value = editor;
};

// 重置表单
const resetForm = async () => {
  try {
    if (editorRef.value) {
      editorRef.value.clear();
      form.message = '';
    }
    form.phone = '';
    form.groupLinks = '';
    form.image = null;
    fileList.value = []; // 清空文件列表
    await nextTick();
    if (adForm.value) {
      adForm.value.resetFields();
    }
    if (uploadRef.value) {
      uploadRef.value.clearFiles(); // 清空上传组件
    }
  } catch (error) {
    console.error('重置表单失败:', error);
    ElMessage.error('重置表单失败，请重试');
  }
};

// 处理群发请求
const handleAdRequest = async () => {
  if (!form.phone.trim() || !form.groupLinks.trim() || !form.message.trim()) {
    ElMessage.warning('请填写手机号、群组链接和消息内容');
    return;
  }

  isLoading.value = true;

  // 使用 FormData 发送图片和数据
  const formData = new FormData();
  formData.append('phone', form.phone);
  formData.append('group_links',form.groupLinks)
  if (form.image) {
    formData.append('image', form.image); // 添加图片文件
  }
  formData.append('message', form.message);
  console.log('🚀 Sending FormData:', [...formData.entries()]);
  try {
    const response = await fetch('http://192.168.6.188:59006/send_message', {
      method: 'POST',
      body: formData, // FormData 会自动设置正确的 Content-Type
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const sendData = await response.json();
    console.log(sendData);

    // 设置结果对话框的数据
    resultStatus.value = sendData.status;
    resultMessage.value = sendData.message || '无';
    resultFailedGroups.value = sendData.failed_groups || [];
    resultChannelGroups.value = sendData.channel_groups || [];

    // 显示结果对话框
    resultDialogVisible.value = true;
  } catch (error) {
    console.error('请求失败:', error);
    resultStatus.value = 'error';
    resultMessage.value = `操作失败：${error.message}`;
    resultFailedGroups.value = [];
    resultChannelGroups.value = [];
    resultDialogVisible.value = true;
  } finally {
    isLoading.value = false;
  }
};

// 组件销毁时销毁编辑器
onBeforeUnmount(() => {
  const editor = editorRef.value;
  if (editor) editor.destroy();
  if (fileList.value.length > 0) {
    fileList.value.forEach(file => URL.revokeObjectURL(file.url));
  }
});
</script>

<style scoped lang="scss">
.ad-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
  position: relative;
}

.top {
  height: 60px;
  background: linear-gradient(
    to right,
    rgb(200, 134, 200),
    rgb(146, 197, 255),
    rgb(64, 154, 250)
  );
  width: 100%;
  font-size: 40px;
  text-align: center;
  line-height: 60px;
  font-weight: 700;
  color: #fff;
}

.content-area {
  padding: 20px;
}

.ad-form {
  .el-form-item {
    margin-bottom: 20px;
  }

  .el-input {
    width: 100%;
  }

  .el-upload__tip {
    color: #606266;
    font-size: 12px;
    margin-top: 8px;
  }
}
</style>