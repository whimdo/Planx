import { createRouter, createWebHistory } from 'vue-router'
import SearchPage from '../views/SearchPage.vue'

const routes = [
    {
        path: '/',
        name: 'Search',
        component: SearchPage
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router