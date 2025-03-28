<!-- MresultDialog.vue -->
<template>
  <el-dialog
    title="发送结果"
    v-model="dialogVisible"
    width="700px"
    :before-close="handleClose"
    :close-on-click-modal="false"
  >
    <div class="result-content">
      <!-- 状态显示 -->
      <div class="status-section">
        <el-tag :type="status === 'success' ? 'success' : 'danger'" size="large">
          {{ status === 'success' ? '发送成功' : '发送存在错误' }}
        </el-tag>
        <p class="status-message">{{ message }}</p>
      </div>

      <!-- 失败的群组 -->
      <div class="failed-groups" v-if="failedGroups.length > 0">
        <h3>失败的群组 ({{ failedGroups.length }})</h3>
        <el-table
          :data="failedGroups"
          style="width: 100%"
          max-height="200"
          border
        >
          <el-table-column prop="group" label="群组链接" width="300" />
          <el-table-column label="失败原因">
            <template #default="scope">
              {{ removeBracketContent(scope.row.error) }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 连接是频道 -->
      <div class="channel-groups" v-if="channelGroups.length > 0">
        <h3>频道链接 ({{ channelGroups.length }})</h3>
        <el-table
          :data="channelGroups"
          style="width: 100%"
          max-height="200"
          border
        >
        <el-table-column label="群组链接">
          <template #default="scope">
            {{ scope.row }} <!-- 直接显示数组元素 -->
          </template>
        </el-table-column>
        </el-table>
      </div>

      <!-- 无数据时的提示 -->
      <el-result
        v-if="failedGroups.length === 0 && channelGroups.length === 0"
        icon="success"
        title="全部发送成功"
        sub-title="所有的链接不存在无法发送或频道链接，全部发送成功"
      >
      </el-result>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button type="primary" @click="closeDialog">确定</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  status: {
    type: String,
    default: 'success', // 'success' 或 'error'
  },
  message: {
    type: String,
    default: '',
  },
  failedGroups: {
    type: Array,
    default: () => [],
  },
  channelGroups: {
    type: Array,
    default: () => [],
  },
});

// 移除括号及括号内的内容
const removeBracketContent = (text) => {
  if (!text) return '';
  // 使用正则表达式移除括号及内容
  return text.replace(/\s*\(.*?\)/g, '').trim();
};

const emit = defineEmits(['update:modelValue', 'close']);

// 双向绑定对话框显示状态
const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

// 关闭对话框的方法
const closeDialog = () => {
  emit('update:modelValue', false); // 明确触发关闭
};

// 关闭对话框前的事件
const handleClose = (done) => {
  emit('close');
  done(); // 调用 done() 以确认关闭
};
</script>

<style scoped lang="scss">
.result-content {
  padding: 0 20px 20px 20px;

  .status-section {
    margin-bottom: 20px;
    text-align: center;

    .status-message {
      margin-top: 10px;
      color: #606266;
      word-break: break-word;
    }
  }

  .failed-groups,
  .channel-groups {
    margin-bottom: 20px;

    h3 {
      margin-bottom: 10px;
      color: #303133;
    }
  }

  .el-table {
    margin-bottom: 20px;
  }
}

.dialog-footer {
  display: flex;
  justify-content: center;
}
</style>