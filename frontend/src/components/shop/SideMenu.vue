<script setup>
// Account / settings menu opened from the ☰ button in the header.
// Desktop: dropdown panel under the header. Phone: drawer from the right.
// Items are UI only for now (functionality comes later); each placeholder is marked TODO.
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import {
  Cancel01Icon, GoogleIcon, AppleIcon, TranslateIcon, Moon02Icon, FavouriteIcon,
  InformationCircleIcon, LegalDocument01Icon, ReturnRequestIcon, Shield01Icon,
  InstagramIcon, ThreadsIcon, WhatsappIcon, ArrowRight01Icon,
} from '@hugeicons/core-free-icons'
import { favourites } from '../../stores/shop.js'
import Icon from './Icon.vue'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['close'])

const panel = ref(null)
const favouriteCount = computed(() => Object.keys(favourites.ids).length)

// TODO: wire these up (auth, i18n, theme, pages).
const settings = computed(() => [
  { id: 'language', icon: TranslateIcon, label: 'Language', value: 'English' },
  { id: 'theme', icon: Moon02Icon, label: 'Theme', value: 'System' },
  { id: 'favourites', icon: FavouriteIcon, label: 'Favourites', count: favouriteCount.value },
])
const pages = [
  { id: 'about', icon: InformationCircleIcon, label: 'About Grocer' },
  { id: 'terms', icon: LegalDocument01Icon, label: 'Terms of service' },
  { id: 'returns', icon: ReturnRequestIcon, label: 'Return policy' },
  { id: 'privacy', icon: Shield01Icon, label: 'Privacy policy' },
]
const socials = [
  { id: 'instagram', icon: InstagramIcon, label: '@grocer.hk' },
  { id: 'threads', icon: ThreadsIcon, label: '@grocer.hk' },
  { id: 'whatsapp', icon: WhatsappIcon, label: 'WhatsApp support' },
]

function onKey(event) {
  if (event.key === 'Escape') emit('close')
}

// Focus the panel when it opens, lock page scroll behind the phone drawer.
watch(
  () => props.open,
  async (open) => {
    document.documentElement.classList.toggle('menu-open', open)
    if (open) {
      window.addEventListener('keydown', onKey)
      await nextTick()
      panel.value?.querySelector('button, a')?.focus()
    } else {
      window.removeEventListener('keydown', onKey)
    }
  },
)
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  document.documentElement.classList.remove('menu-open')
})
</script>

<template>
  <Teleport to="body">
    <Transition name="menu-fade">
      <div v-if="open" class="menu-backdrop" @click="emit('close')" />
    </Transition>
    <Transition name="menu-slide">
      <aside
        v-if="open"
        id="side-menu"
        ref="panel"
        class="side-menu"
        role="dialog"
        aria-modal="true"
        aria-label="Menu"
      >
        <div class="menu-top">
          <span class="menu-title">Menu</span>
          <button type="button" class="menu-close" aria-label="Close menu" @click="emit('close')">
            <Icon :icon="Cancel01Icon" :size="20" />
          </button>
        </div>

        <!-- Sign in (placeholder) -->
        <section class="menu-section menu-auth">
          <p class="menu-hint">Sign in to save your carts and preferences.</p>
          <button type="button" class="auth-btn auth-google">
            <Icon :icon="GoogleIcon" :size="18" /> Continue with Google
          </button>
          <button type="button" class="auth-btn auth-apple">
            <Icon :icon="AppleIcon" :size="18" /> Continue with Apple
          </button>
        </section>

        <!-- Settings -->
        <section class="menu-section">
          <button v-for="item in settings" :key="item.id" type="button" class="menu-row">
            <Icon :icon="item.icon" :size="20" class="menu-row-icon" />
            <span class="menu-row-text">
              <span v-if="item.value" class="menu-row-label">{{ item.label }}</span>
              <span :class="item.value ? 'menu-row-value' : 'menu-row-main'">{{ item.value ?? item.label }}</span>
            </span>
            <span v-if="item.count" class="menu-count">{{ item.count }}</span>
            <Icon :icon="ArrowRight01Icon" :size="16" class="menu-row-chevron" />
          </button>
        </section>

        <!-- Info pages -->
        <section class="menu-section">
          <button v-for="item in pages" :key="item.id" type="button" class="menu-row">
            <Icon :icon="item.icon" :size="20" class="menu-row-icon" />
            <span class="menu-row-main">{{ item.label }}</span>
          </button>
        </section>

        <!-- Socials -->
        <section class="menu-section">
          <p class="menu-caption">Follow us</p>
          <button v-for="item in socials" :key="item.id" type="button" class="menu-row">
            <Icon :icon="item.icon" :size="20" class="menu-row-icon" />
            <span class="menu-row-main">{{ item.label }}</span>
          </button>
        </section>
      </aside>
    </Transition>
  </Teleport>
</template>
