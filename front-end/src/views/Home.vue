<template>
  <div class="common-layout">
    <el-container>
      <!-- 侧边栏：图标置于顶部，新增菜单 -->
      <el-aside width="150px" class="aside">
        <img src="@/assets/icon.png" alt="Search Icon" class="aside-icon" />
        <el-menu
          :default-active="activeMenu"
          class="aside-menu"
          @select="handleMenuSelect"
          active-text-color="#ffd04b" background-color="transparent" text-color="#fff"
        >
          <el-menu-item index="search">
            <el-icon>
              <Search />
            </el-icon>
            <span>搜索群组</span>
          </el-menu-item>
          <el-menu-item index="ai">
            <el-icon>
              <ChatDotRound />
            </el-icon>
            <span>AI助手</span>
          </el-menu-item>
          <el-menu-item index="ad">
            <el-icon>
              <TakeawayBox/>
            </el-icon>
            <span>广告转发</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主容器 -->
      <el-container>
        <!-- 头部：文字图片 -->
        <el-header class="header">
          <img src="@/assets/title.png" alt="Search Text" class="header-text" style="width: 500px; height: auto;" />
        </el-header>

        <!-- 主内容：动态切换卡片 -->
        <el-main class="main">
          <search-card v-if="activeMenu === 'search'" />
          <ai-card v-if="activeMenu === 'ai'" />
          <ad-card v-if="activeMenu === 'ad'" />
        </el-main>

        <!-- 底部 -->
        <el-footer class="footer">
          @Planx eSearch1.0
        </el-footer>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SearchCard from '@/components/SearchCard.vue'
import AiCard from '@/components/AiCard.vue'
import AdCard from '@/components/AdCard.vue'
import { Search, ChatDotRound, TakeawayBox} from '@element-plus/icons-vue'


// 控制当前选中的菜单项
const activeMenu = ref('search') // 默认显示搜索群组

// 处理菜单选择
const handleMenuSelect = (index) => {
  activeMenu.value = index
}
</script>

<style scoped>
/* 全局重置 */
:global(html, body, #app) {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  box-sizing: border-box;
}

.common-layout {
  height: 100vh;
  width: 100vw;
  display: flex;
  overflow: hidden;
  background: white;
}

.aside {
  background: linear-gradient(to bottom, #409afa, #7dc8ec);
  width: 150px !important;
  height: 100vh !important;
  position: fixed !important;
  left: 0;
  top: 0;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.aside-icon {
  width: 80px;
  height: 80px;
  margin: 30px 0 20px 0;
  object-fit: contain;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
}

.aside-menu {
  width: 100%;
  background: transparent;
  border: none;
}

.el-container > .el-container {
  margin-left: 150px !important;
  width: calc(100vw - 150px) !important;
  min-height: 100vh;
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
  overflow: hidden;
  display: flex;
}

.footer {
  height: 50px !important;
  line-height: 50px;
  text-align: center;
  background-color: #f5f7fa;
}
</style>