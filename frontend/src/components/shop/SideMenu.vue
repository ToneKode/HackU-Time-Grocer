<script setup>
// Account / settings menu opened from the ☰ button in the header.
// Desktop: dropdown panel under the header. Phone: drawer from the right.
// Language switching works; the other items are UI only for now (marked TODO).
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import {
  Cancel01Icon, GoogleIcon, AppleIcon, TranslateIcon, Moon02Icon, FavouriteIcon,
  InformationCircleIcon, LegalDocument01Icon, ReturnRequestIcon, Shield01Icon,
  InstagramIcon, ThreadsIcon, WhatsappIcon, ArrowRight01Icon, ArrowLeft01Icon, Tick02Icon,
} from '@hugeicons/core-free-icons'
import { useI18n } from 'vue-i18n'
import { LOCALES, setLocale } from '../../i18n/index.js'
import { favourites } from '../../stores/shop.js'
import Icon from './Icon.vue'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['close'])

const panel = ref(null)
const view = ref('main') // 'main' | 'language'
const { t, locale } = useI18n()
const currentLanguage = computed(() => LOCALES.find((l) => l.code === locale.value)?.label)

async function showView(name) {
  view.value = name
  await nextTick()
  panel.value?.querySelector('.menu-view button')?.focus()
}

function chooseLanguage(code) {
  setLocale(code)
  showView('main')
}
const favouriteCount = computed(() => Object.keys(favourites.ids).length)

// TODO: wire up auth, theme, favourites page and info pages.
const settings = computed(() => [
  { id: 'language', icon: TranslateIcon, label: t('menu.language'), value: currentLanguage.value, action: () => showView('language') },
  { id: 'theme', icon: Moon02Icon, label: t('menu.theme'), value: t('menu.themeSystem') },
  { id: 'favourites', icon: FavouriteIcon, label: t('menu.favourites'), count: favouriteCount.value },
])
const pages = computed(() => [
  { id: 'about', icon: InformationCircleIcon, label: t('menu.about') },
  { id: 'terms', icon: LegalDocument01Icon, label: t('menu.terms') },
  { id: 'returns', icon: ReturnRequestIcon, label: t('menu.returns') },
  { id: 'privacy', icon: Shield01Icon, label: t('menu.privacy') },
])
const socials = computed(() => [
  { id: 'instagram', icon: InstagramIcon, label: '@grocer.hk' },
  { id: 'threads', icon: ThreadsIcon, label: '@grocer.hk' },
  { id: 'whatsapp', icon: WhatsappIcon, label: t('menu.whatsapp') },
])

function onKey(event) {
  if (event.key === 'Escape') emit('close')
}

// Focus the panel when it opens, lock page scroll behind the phone drawer.
watch(
  () => props.open,
  async (open) => {
    document.documentElement.classList.toggle('menu-open', open)
    if (open) {
      view.value = 'main'
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
        :aria-label="$t('menu.title')"
      >
        <div class="menu-top">
          <span class="menu-title">{{ $t('menu.title') }}</span>
          <button type="button" class="menu-close" :aria-label="$t('menu.close')" @click="emit('close')">
            <Icon :icon="Cancel01Icon" :size="20" />
          </button>
        </div>

        <!-- Language picker -->
        <section v-if="view === 'language'" class="menu-section menu-view">
          <button type="button" class="menu-row menu-back" @click="showView('main')">
            <Icon :icon="ArrowLeft01Icon" :size="18" class="menu-row-icon" />
            <span class="menu-row-main">{{ $t('menu.chooseLanguage') }}</span>
          </button>
          <button
            v-for="l in LOCALES"
            :key="l.code"
            type="button"
            class="menu-row"
            :lang="l.code"
            :aria-pressed="locale === l.code"
            @click="chooseLanguage(l.code)"
          >
            <span class="menu-row-main" :class="{ 'menu-row-value': locale === l.code }">{{ l.label }}</span>
            <Icon v-if="locale === l.code" :icon="Tick02Icon" :size="18" class="menu-check" />
          </button>
        </section>

        <template v-else>
        <!-- Sign in (placeholder) -->
        <section class="menu-section menu-auth">
          <p class="menu-hint">{{ $t('menu.signInHint') }}</p>
          <button type="button" class="auth-btn auth-google">
            <Icon :icon="GoogleIcon" :size="18" /> {{ $t('menu.google') }}
          </button>
          <button type="button" class="auth-btn auth-apple">
            <Icon :icon="AppleIcon" :size="18" /> {{ $t('menu.apple') }}
          </button>
        </section>

        <!-- Settings -->
        <section class="menu-section menu-view">
          <button v-for="item in settings" :key="item.id" type="button" class="menu-row" @click="item.action?.()">
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
          <p class="menu-caption">{{ $t('menu.followUs') }}</p>
          <button v-for="item in socials" :key="item.id" type="button" class="menu-row">
            <Icon :icon="item.icon" :size="20" class="menu-row-icon" />
            <span class="menu-row-main">{{ item.label }}</span>
          </button>
        </section>
        </template>
      </aside>
    </Transition>
  </Teleport>
</template>
