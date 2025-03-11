<template>
    <div class="common-layout">
        <el-container>
            <!-- 侧边栏：图标置于顶部 -->
            <el-aside width="150px" class="aside">
                <img src="@/assets/icon.png" alt="Search Icon" class="aside-icon" />
            </el-aside>
        
        <!-- 主容器 -->
        <el-container>
            <!-- 头部：文字图片 -->
            <el-header class="header">
                <img src="@/assets/title.png" alt="Search Text" class="header-text" style="width: 500px; height: auto;" />
            </el-header>
            <!-- 主内容：搜索输入框、表格和分页放入 el-card -->
            <el-main class="main">
                <el-card class="search-card">
            <!-- 修改后的搜索表单 -->
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="搜索内容：">
                  <el-input v-model="searchQuery" placeholder="请输入搜索内容" clearable />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="最大结果数：">
                  <el-input
                    v-model.number="searchCount"
                    placeholder="请输入数量"
                    type="number"
                    min="1"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="4">
                <el-button type="primary" @click="handleSearch" :loading="isLoading">{{ isLoading ? '搜索中...' : '搜索' }}</el-button>
              </el-col>
            </el-row>

                  <!-- 群组卡片展示 -->
      <div v-if="groups.length > 0" class="group-container">
        <el-row :gutter="20" class="group-row">
          <el-col 
            v-for="(group, index) in paginatedGroups"
            :key="index"
            :span="8"
            class="group-col"
          >
            <el-card class="group-card" shadow="hover">
              <!-- 群组头像 -->
              <div class="group-avatar">
                <el-avatar 
                  :size="80"
                  :src="getAvatarSrc(group.avatar)"
                  shape="square"
                />
              </div>

              <!-- 群组基本信息 -->
              <div class="group-info">
                <h3 class="group-name">{{ group.name }}</h3>
                <div class="group-meta">
                  <el-tag 
                    type="info" 
                    size="small"
                    class="group-type"
                  >
                    {{ group.type }}
                  </el-tag>
                  <div class="member-count">
                    <el-icon><User /></el-icon>
                    <span>{{ group.member_count.toLocaleString() }}</span>
                  </div>
                </div>
              </div>

              <!-- 加入按钮 -->
              <div class="group-actions">
                <el-button 
                  type="primary" 
                  plain 
                  @click="openGroupLink(group.url)"
                  class="join-button"
                >
                  <el-icon class="el-icon--right"><Link /></el-icon>
                  立即加入
                </el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

            <!-- 修改后的分页（固定每页6条） -->
            <el-pagination
                v-if="groups.length > 0"
                v-model:current-page="currentPage"
                :page-size="6"
                :total="totalGroups"
                layout="prev, pager, next, jumper"
                class="custom-pagination"
            />
          </el-card>
        </el-main>
          
          <!-- 底部（可选） -->
          <el-footer class="footer">
            @Planx eSearch1.0
          </el-footer>
        </el-container>
      </el-container>
    </div>
  </template>
  
  <script setup>
import { ref, computed } from 'vue'
import { User, Link } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 响应式数据
const searchQuery = ref('')
const searchCount = ref(6) // 默认获取9条
const groups = ref([])
const totalGroups = ref(0)
const currentPage = ref(1)
const isLoading = ref(false)

// 处理base64头像
const getAvatarSrc = (base64) => {
  return base64 ? `data:image/png;base64,${base64}` : '/default-group-avatar.png'
}

// 处理搜索请求
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }

  try {
    isLoading.value = true
    
    // 构造请求参数
    const requestBody = {
      text: searchQuery.value.trim(),
      keyword_count:20,
      top_k: Number(searchCount.value) || 6
    }

    // 发送POST请求
    const response = await fetch('http://192.168.1.208:9006/query_group_info/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // const data = await response.json()

    // // 处理返回数据
    // groups.value = data.group_info || []
    // totalGroups.value = data.search_count || 0
    const data = await response.json();
    groups.value = (data.group_info || []).filter(group => group !== null); // 过滤 null
    totalGroups.value = data.group_ids?.length || 0; // 使用 group_ids 长度
    
    ElMessage.success(`找到 ${totalGroups.value} 个相关群组`)
  } catch (error) {
    console.error('搜索失败:', error)
    ElMessage.error(`搜索失败: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

// 分页处理
const paginatedGroups = computed(() => {
  const start = (currentPage.value - 1) * 6
  return groups.value.slice(start, start + 6)
})

// 打开群链接
const openGroupLink = (url) => {
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}
</script>


<style scoped>
/* 全局重置 */
/* 全局重置增强版 */
:global(html, body, #app) {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  box-sizing: border-box;
}

:global(.el-container) {
  border: none !important;
  box-shadow: none !important;
}

.common-layout {
  height: 100vh;
  width: 100vw;
  display: flex;
  overflow: hidden;
  background: white; /* 确保底色统一 */
}

/* 侧边栏绝对定位方案 */
.aside {
  background: linear-gradient(to bottom, #409afa, #7dc8ec);
  width: 150px !important;
  height: 100vh !important;
  margin: 0 !important;
  padding: 0 !important;
  position: fixed !important;
  left: 0;
  top: 0;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 主内容区偏移 */
.el-container > .el-container {
  margin-left: 150px !important;
  width: calc(100vw - 150px) !important;
  min-height: 100vh;
}

/* 图标定位微调 */
.aside-icon {
  width: 80px;
  height: 80px;
  margin: 30px 0 0 0;
  object-fit: contain;
  flex-shrink: 0;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
}

/* 可选悬停效果 */
.aside-icon:hover {
  transform: translateY(-2px);
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
}

/* 主容器布局调整 */
.el-container > .el-container {
  flex: 1;
  flex-direction: column;
  min-width: 0; /* 防止flex溢出 */
}

.header {
  height: 60px !important;
  padding: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #e6e6e6;
}

.main {
  flex: 1;
  padding: 20px;
  overflow: hidden; /* 禁止主区域滚动 */
  display: flex;
}

.search-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 禁止卡片溢出 */
}

/* 表格区域添加滚动 */
.el-table {
  flex: 1;
  overflow: auto; /* 只在表格区域滚动 */
}

.footer {
  height: 50px !important;
  line-height: 50px;
  text-align: center;
  background-color: #f5f7fa;
}

/* 移除Element Plus默认边距 */
:global(
  .el-aside,
  .el-header,
  .el-main,
  .el-footer,
  .el-container
) {
  margin: 0 !important;
  padding: 0 !important;
}

/* 修正表单元素间距 */
:global(.el-form-item) {
  margin-bottom: 0 !important;
}

.group-card {
  height: 240px;
  display: flex;
  flex-direction: column;
  margin: 8px;
  transition: transform 0.2s;
}

.group-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.group-avatar {
  text-align: center;
  margin: 16px 0;
}

.group-avatar :deep(.el-avatar) {
  border: 2px solid #409EFF;
  border-radius: 8px;
}

.group-info {
  flex: 1;
  padding: 0 16px;
}

.group-name {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  white-space: nowrap; /* 禁止换行 */
  overflow: hidden; /* 隐藏超出内容 */
  text-overflow: ellipsis; /* 超出部分显示 ... */
}

.group-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}

.group-type {
  font-size: 12px;
}

.member-count {
  display: flex;
  align-items: center;
  color: #909399;
  font-size: 12px;
}

.member-count .el-icon {
  margin-right: 4px;
}

.group-actions {
  border-top: 1px solid #EBEEF5;
  padding: 16px;
  text-align: center;
}

.join-button {
  width: 100%;
}

.custom-pagination {
  margin-top: 24px;
  justify-content: center;
}

@media (max-width: 768px) {
  .group-card {
    height: auto;
  }
  
  .group-name {
    font-size: 14px;
  }
}

.loading-container {
  text-align: center;
  padding: 40px 0;
  color: #909399;
}

.loading-container .el-icon {
  animation: rotating 2s linear infinite;
  margin-bottom: 10px;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>