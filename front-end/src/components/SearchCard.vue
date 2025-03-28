<template>
    <el-card class="search-card">
      <!-- 搜索表单 -->
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
          <el-button type="primary" @click="handleSearch" :loading="isLoading">
            {{ isLoading ? '搜索中...' : '搜索' }}
          </el-button>
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
              <div class="group-avatar">
                <el-avatar
                  :size="80"
                  :src="getAvatarSrc(group.avatar)"
                  shape="square"
                />
              </div>
              <div class="group-info">
                <h3 class="group-name">{{ group.name }}</h3>
                <div class="group-meta">
                  <el-tag type="info" size="small" class="group-type">
                    {{ group.type }}
                  </el-tag>
                  <div class="member-count">
                    <el-icon><User /></el-icon>
                    <span>{{ group.member_count.toLocaleString() }}</span>
                  </div>
                </div>
              </div>
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
  
      <!-- 分页 -->
      <el-pagination
        v-if="groups.length > 0"
        v-model:current-page="currentPage"
        :page-size="6"
        :total="totalGroups"
        layout="prev, pager, next, jumper"
        class="custom-pagination"
      />
    </el-card>
  </template>
  
  <script setup>
  import { ref, computed } from 'vue'
  import { User, Link } from '@element-plus/icons-vue'
  import { ElMessage } from 'element-plus'
  
  const searchQuery = ref('')
  const searchCount = ref(6)
  const groups = ref([])
  const totalGroups = ref(0)
  const currentPage = ref(1)
  const isLoading = ref(false)
  
  const getAvatarSrc = (base64) => {
    return base64 ? `data:image/png;base64,${base64}` : '/default-group-avatar.png'
  }
  
  const handleSearch = async () => {
    if (!searchQuery.value.trim()) {
      ElMessage.warning('请输入搜索内容')
      return
    }
  
    try {
      isLoading.value = true
      const requestBody = {
        text: searchQuery.value.trim(),
        keyword_count: 20,
        top_k: Number(searchCount.value) || 6
      }
  
      const response = await fetch('http://192.168.6.188:51006/query_group_info/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      })
  
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
  
      const data = await response.json()
      groups.value = (data.group_info || []).filter(group => group !== null)
      totalGroups.value = data.group_ids?.length || 0
  
      ElMessage.success(`找到 ${totalGroups.value} 个相关群组`)
    } catch (error) {
      console.error('搜索失败:', error)
      ElMessage.error(`搜索失败: ${error.message}`)
    } finally {
      isLoading.value = false
    }
  }
  
  const paginatedGroups = computed(() => {
    const start = (currentPage.value - 1) * 6
    return groups.value.slice(start, start + 6)
  })
  
  const openGroupLink = (url) => {
    if (!url) return
    window.open(url, '_blank', 'noopener,noreferrer')
  }
  </script>
  
  <style scoped>
  .search-card {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  
  .group-container {
    flex: 1;
    overflow: auto;
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
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
  </style>