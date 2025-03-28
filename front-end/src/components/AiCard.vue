<template>
  <el-card class="search-card">
    <div class="top">AI 助手</div>
    <div class="chat-area">
      <div class="group-container chat" ref="chatContainer">
        <div
          v-for="(item, i) in msgList"
          :key="i"
          :class="item.type === '1' ? 'rightMsg' : 'leftMsg'"
        >
          <img
            v-if="item.type === '0'"
            src="@/assets/AI1.jpg"
            alt="AI Avatar"
          />
          <div class="msg">{{ item.content }}</div>
          <img
            v-if="item.type === '1'"
            src="@/assets/user.jpg"
            alt="User Avatar"
          />
        </div>
      </div>
    </div>
    <div class="bottom">
      <input v-model="aiInput" placeholder="请输入您的问题或指令..." />
      <button @click="handleAIRequest" :disabled="isLoading">
        <el-icon :size="20">
          <Position />
        </el-icon>
      </button>
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Position } from '@element-plus/icons-vue'

// 响应式数据
const aiInput = ref('')
const msgList = reactive([])
const isLoading = ref(false)
const chatContainer = ref(null)

// 自动滚动到最新消息
const scrollToNew = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

// 添加用户消息
const addUserMessage = (content) => {
  const userMsg = {
    content,
    type: '1', // 用户消息
    id: Date.now()
  }
  msgList.push(userMsg)
}

// 添加AI回复
const addAIResponse = (content) => {
  const aiMsg = {
    content,
    type: '0', // AI消息
    id: Date.now()
  }
  msgList.push(aiMsg)
}

// 处理AI请求
const handleAIRequest = async () => {
  if (!aiInput.value.trim()) {
    ElMessage.warning('请输入内容')
    return
  }

  try {
    isLoading.value = true
    addUserMessage(aiInput.value)
    scrollToNew()

    const response = await fetch('http://192.168.6.188:59006/ai_assistant/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: aiInput.value.trim() })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    addAIResponse(data.response || '暂无回答')
    scrollToNew()
  } catch (error) {
    console.error('AI请求失败:', error)
    ElMessage.error(`请求失败: ${error.message}`)
    addAIResponse('抱歉，请求失败，请稍后重试')
    scrollToNew()
  } finally {
    aiInput.value = ''
    isLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.search-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
  position: relative;
}

.top {
  height: 70px;
  background: linear-gradient(
    to right,
    rgb(200, 134, 200),
    rgb(146, 197, 255),
    rgb(64, 154, 250)
  );
  width: 100%;
  font-size: 50px;
  text-align: center;
  line-height: 70px;
  font-weight: 900;
  color: #fff;
  flex-shrink: 0;
}

.chat-area {
  flex: 1;
  margin: 10px;
  background-color: rgba(255, 255, 255, 0);
  border-radius: 10px;
  height: 580px;
  overflow: hidden;
  //box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.group-container.chat {
  height: 100%;
  overflow-y: auto;
  padding: 10px;

  .leftMsg,
  .rightMsg {
    display: flex;
    flex-direction: row;
    justify-content: start;
    align-items: center;
    margin: 10px;

    img {
      width: 40px;
      height: 40px;
      border-radius: 20px;
      overflow: hidden;
      object-fit: cover;
      margin: 0 10px;
    }

    .msg {
      display: inline-block;
      padding: 10px;
      word-wrap: anywhere;
      max-width: 600px;
      background-color: #364d79;
      border-radius: 10px;
      color: #fff;
    }
  }

  .rightMsg {
    justify-content: end;

    .msg {
      color: black;
      background-color: #dfdfdf;
    }
  }
}

.bottom {
  height: 45px;
  display: flex;
  align-items: center;
  width: 80%;
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;

  input {
    width: 90%;
    border: 1px solid rgb(171, 171, 171);
    border-right: none;
    height: 40px;
    color: black;
    text-indent: 2px;
    line-height: 40px;
    border-radius: 10px 0 0 10px;
  }

  button {
    cursor: pointer;
    width: 10%;
    border: none;
    outline: none;
    height: 45px;
    border-radius: 0 10px 10px 0;
    background: linear-gradient(to right, rgb(146, 197, 255), rgb(200, 134, 200));
    display: flex;
    align-items: center;
    justify-content: center;

    &[disabled] {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .el-icon {
      color: #fff;
    }
  }
}
</style>