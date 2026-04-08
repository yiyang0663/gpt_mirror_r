<template>
  <div :class="sideNavCls">
    <div class="admin-side-panel" :class="{ 'is-collapsed': collapsed }">
      <button class="admin-side-brand" type="button" @click="goHome">
        <span class="admin-side-brand-mark">
          <asset-logo class="admin-side-brand-icon" />
        </span>
        <span v-if="!collapsed" class="admin-side-brand-copy">
          <strong>ChatGPT Mirror</strong>
          <small>Admin Console</small>
        </span>
      </button>

      <button class="admin-side-primary" type="button" @click="goPortal">
        <t-icon name="browse" />
        <span v-if="!collapsed">打开 C 端</span>
      </button>

      <div v-if="!collapsed" class="admin-side-section">Operations</div>

      <t-menu class="admin-side-menu" :theme="theme" :value="active" :collapsed="collapsed" :default-expanded="defaultExpanded">
        <menu-content :nav-data="menu" />
      </t-menu>

      <div class="admin-side-footer">
        <div class="admin-side-status">
          <span class="admin-side-status-dot"></span>
          <span v-if="!collapsed">Site Live · Push Deploy</span>
        </div>
        <p v-if="!collapsed" class="admin-side-caption">用户、上游账号、资源池和系统审计统一在这一侧完成值守。</p>
      </div>
    </div>
    <div :class="`${prefix}-side-nav-placeholder${collapsed ? '-hidden' : ''}`"></div>
  </div>
</template>

<script setup lang="ts">
import union from 'lodash/union';
import type { PropType } from 'vue';
import { computed, onBeforeUnmount, onMounted } from 'vue';
import { useRouter } from 'vue-router';

import AssetLogo from '@/assets/openai-logo.svg?component';
import { prefix } from '@/config/global';
import { getActive, getRoutesExpanded } from '@/router';
import { useSettingStore } from '@/store';
import type { MenuRoute, ModeType } from '@/types/interface';

import MenuContent from './MenuContent.vue';

const MIN_POINT = 992 - 1;

defineProps({
  menu: {
    type: Array as PropType<MenuRoute[]>,
    default: () => [],
  },
  showLogo: {
    type: Boolean as PropType<boolean>,
    default: true,
  },
  isFixed: {
    type: Boolean as PropType<boolean>,
    default: true,
  },
  layout: {
    type: String as PropType<string>,
    default: '',
  },
  headerHeight: {
    type: String as PropType<string>,
    default: '64px',
  },
  theme: {
    type: String as PropType<ModeType>,
    default: 'light',
  },
  isCompact: {
    type: Boolean as PropType<boolean>,
    default: false,
  },
});

const collapsed = computed(() => useSettingStore().isSidebarCompact);
const active = computed(() => getActive());

const defaultExpanded = computed(() => {
  const path = getActive();
  const parentPath = path.substring(0, path.lastIndexOf('/'));
  const expanded = getRoutesExpanded();
  return union(expanded, parentPath === '' ? [] : [parentPath]);
});

const sideNavCls = computed(() => [`${prefix}-sidebar-layout`]);

const settingStore = useSettingStore();
const router = useRouter();

const autoCollapsed = () => {
  const isCompact = window.innerWidth <= MIN_POINT;
  settingStore.updateConfig({
    isSidebarCompact: isCompact,
  });
};

const handleResize = () => {
  autoCollapsed();
};

onMounted(() => {
  autoCollapsed();
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
});

const goHome = () => {
  router.push('/overview');
};

const goPortal = () => {
  window.open('/#/customer/chat', '_blank', 'noopener,noreferrer');
};
</script>

<style lang="less" scoped>
.admin-side-panel {
  position: fixed;
  inset: 14px auto 14px 14px;
  display: flex;
  flex-direction: column;
  width: 252px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 28px;
  background:
    radial-gradient(circle at top, rgba(16, 163, 127, 0.18), transparent 38%),
    linear-gradient(180deg, rgba(12, 18, 28, 0.98) 0%, rgba(15, 23, 42, 0.98) 100%);
  box-shadow:
    0 24px 60px rgba(15, 23, 42, 0.32),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(14px);
}

.admin-side-panel.is-collapsed {
  width: 76px;
  align-items: center;
}

.admin-side-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 8px 10px 12px;
  border: none;
  background: transparent;
  color: #f8fafc;
  cursor: pointer;
  text-align: left;
}

.admin-side-brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.admin-side-brand-icon {
  width: 22px;
  height: 22px;
}

.admin-side-brand-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.admin-side-brand-copy strong {
  color: #f8fafc;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.2;
}

.admin-side-brand-copy small {
  color: rgba(226, 232, 240, 0.68);
  font-size: 12px;
  line-height: 1.3;
}

.admin-side-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  min-height: 44px;
  margin: 4px 0 16px;
  padding: 0 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  box-shadow:
    0 10px 30px rgba(15, 23, 42, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  color: #f8fafc;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease;
}

.admin-side-primary:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.16);
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.24);
}

.admin-side-panel.is-collapsed .admin-side-primary {
  width: 48px;
  padding: 0;
}

.admin-side-section {
  margin: 0 10px 8px;
  color: rgba(148, 163, 184, 0.72);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.admin-side-menu {
  flex: 1;
  min-height: 0;
  padding: 0;
  border: none;
  background: transparent;
}

.admin-side-menu:deep(.t-default-menu__inner) {
  background: transparent;
}

.admin-side-menu:deep(.t-menu__operations) {
  display: none;
}

.admin-side-menu:deep(.t-menu__item),
.admin-side-menu:deep(.t-submenu__title) {
  height: auto;
  margin: 2px 0;
  padding: 12px 12px 12px 14px;
  border-radius: 16px;
  color: rgba(226, 232, 240, 0.84);
  font-size: 14px;
  transition:
    background-color 180ms ease,
    box-shadow 180ms ease,
    color 180ms ease;
}

.admin-side-menu:deep(.t-menu__item:hover),
.admin-side-menu:deep(.t-submenu__title:hover) {
  background: rgba(255, 255, 255, 0.08);
}

.admin-side-menu:deep(.t-menu__item .t-icon),
.admin-side-menu:deep(.t-submenu__title .t-icon) {
  margin-right: 12px;
  color: rgba(148, 163, 184, 0.82);
}

.admin-side-menu:deep(.t-is-active:not(.t-is-opened)),
.admin-side-menu:deep(.t-is-active > .t-submenu__title) {
  background:
    linear-gradient(135deg, rgba(16, 163, 127, 0.22) 0%, rgba(30, 41, 59, 0.72) 100%),
    rgba(255, 255, 255, 0.08);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.08),
    0 12px 30px rgba(15, 23, 42, 0.24);
  color: #fff;
}

.admin-side-menu:deep(.t-is-active .t-icon) {
  color: #10a37f;
}

.admin-side-menu:deep(.t-submenu__content) {
  margin-left: 16px;
  padding-left: 10px;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
}

.admin-side-panel.is-collapsed .admin-side-menu:deep(.t-menu__item),
.admin-side-panel.is-collapsed .admin-side-menu:deep(.t-submenu__title) {
  justify-content: center;
  padding: 12px 0;
}

.admin-side-panel.is-collapsed .admin-side-menu:deep(.t-menu__item .t-icon),
.admin-side-panel.is-collapsed .admin-side-menu:deep(.t-submenu__title .t-icon) {
  margin-right: 0;
}

.admin-side-footer {
  padding: 14px 8px 4px;
}

.admin-side-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(226, 232, 240, 0.82);
  font-size: 12px;
  font-weight: 600;
}

.admin-side-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #10a37f;
  box-shadow: 0 0 0 5px rgba(16, 163, 127, 0.18);
}

.admin-side-caption {
  margin: 12px 4px 0;
  color: rgba(148, 163, 184, 0.74);
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 991px) {
  .admin-side-panel {
    inset: 12px auto 12px 12px;
  }
}
</style>
