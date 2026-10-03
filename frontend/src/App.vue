<script setup>
import { useRoute } from 'vue-router'
import AppHeader from './components/shop/AppHeader.vue'
import SiteFooter from './components/shop/SiteFooter.vue'

const route = useRoute()
</script>

<template>
  <AppHeader v-if="!route.meta.hideHeader" />
  <RouterView />
  <SiteFooter />
</template>
