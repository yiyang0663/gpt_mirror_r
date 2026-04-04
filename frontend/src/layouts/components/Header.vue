<template>
  <div :class="layoutCls">
    <div :class="menuCls">
      <div class="admin-header-shell">
        <div class="admin-header-leading">
          <t-button class="admin-header-toggle" theme="default" shape="square" variant="text" @click="changeCollapsed">
            <t-icon class="collapsed-icon" name="view-list" />
          </t-button>

          <div class="admin-header-copy">
            <p class="admin-header-section">{{ sectionTitle }}</p>
            <button class="admin-header-title" type="button" @click="handleNav(homePath)">
              {{ currentTitle }}
            </button>
          </div>
        </div>

        <div class="admin-header-actions">
          <button class="admin-header-link" type="button" @click="goPortal">用户端</button>

          <notice />

          <t-tooltip placement="bottom" :content="$t('layout.header.code')">
            <t-button class="admin-header-icon-btn" theme="default" shape="square" variant="text" @click="navToGitHub">
              <t-icon name="logo-github" />
            </t-button>
          </t-tooltip>

          <t-dropdown :min-column-width="160" trigger="click">
            <template #dropdown>
              <t-dropdown-menu>
                <t-dropdown-item class="operations-dropdown-container-item" @click="handleLogout">
                  <poweroff-icon />
                  {{ $t('layout.header.signOut') }}
                </t-dropdown-item>
              </t-dropdown-menu>
            </template>
            <t-button class="header-user-btn" theme="default" variant="text">
              <span class="header-user-badge">{{ userInitial }}</span>
              <div class="header-user-meta">
                <span class="header-user-label">{{ displayName }}</span>
                <small class="header-user-role">Admin</small>
              </div>
              <template #suffix><chevron-down-icon /></template>
            </t-button>
          </t-dropdown>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Cookies from 'js-cookie';
import { ChevronDownIcon, PoweroffIcon } from 'tdesign-icons-vue-next';
import type { PropType } from 'vue';
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { prefix } from '@/config/global';
import { useLocale } from '@/locales/useLocale';
import { useSettingStore, useUserStore } from '@/store';
import type { MenuRoute } from '@/types/interface';

import Notice from './Notice.vue';

defineProps({
  theme: {
    type: String,
    default: 'light',
  },
  layout: {
    type: String,
    default: 'top',
  },
  showLogo: {
    type: Boolean,
    default: true,
  },
  menu: {
    type: Array as PropType<MenuRoute[]>,
    default: () => [],
  },
  isFixed: {
    type: Boolean,
    default: false,
  },
  isCompact: {
    type: Boolean,
    default: false,
  },
  maxLevel: {
    type: Number,
    default: 3,
  },
});

const router = useRouter();
const route = useRoute();
const settingStore = useSettingStore();
const user = useUserStore();
const { locale } = useLocale();

const layoutCls = computed(() => [`${prefix}-header-layout`]);
const menuCls = computed(() => ['admin-header-menu']);

const renderTitle = (title?: string | Record<string, string>) => {
  if (!title) return '管理中心';
  if (typeof title === 'string') return title;
  return title[locale.value] || title.zh_CN || title.en_US;
};

const parentRoute = computed(() => {
  if (route.matched.length <= 1) return null;
  return route.matched[route.matched.length - 2];
});

const currentTitle = computed(() => renderTitle(route.meta.title as string | Record<string, string> | undefined));
const sectionTitle = computed(() => renderTitle(parentRoute.value?.meta?.title as string | Record<string, string> | undefined));
const homePath = computed(() => {
  const redirect = parentRoute.value?.redirect;
  if (typeof redirect === 'string') return redirect;
  return parentRoute.value?.path || '/account/chatgpt';
});
const displayName = computed(() => user.userInfo.name || 'Administrator');
const userInitial = computed(() => displayName.value.trim().charAt(0).toUpperCase() || 'A');

const changeCollapsed = () => {
  settingStore.updateConfig({
    isSidebarCompact: !settingStore.isSidebarCompact,
  });
};

const handleNav = (url: string) => {
  router.push(url);
};

const handleLogout = async () => {
  await user.logout();
  Cookies.remove('user_token');
  router.push({
    path: '/login',
    query: { redirect: encodeURIComponent(router.currentRoute.value.fullPath) },
  });
};

const goPortal = () => {
  window.open('/', '_blank', 'noopener,noreferrer');
};

const navToGitHub = () => {
  window.open('https://github.com/dairoot/ChatGPT-Mirror');
};
</script>

<style lang="less" scoped>
.admin-header-menu {
  padding: 14px 28px 0 18px;
}

.admin-header-shell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 74px;
  padding: 16px 20px;
  border: 1px solid rgba(17, 17, 17, 0.06);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow:
    0 18px 48px rgba(17, 17, 17, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(14px);
}

.admin-header-leading,
.admin-header-actions {
  display: flex;
  align-items: center;
}

.admin-header-leading {
  gap: 12px;
  min-width: 0;
}

.admin-header-actions {
  gap: 10px;
}

.admin-header-toggle,
.admin-header-icon-btn {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: rgba(17, 17, 17, 0.04);
  color: #303030;
}

.admin-header-copy {
  min-width: 0;
}

.admin-header-section {
  margin: 0 0 4px;
  color: #7d7d79;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.admin-header-title {
  max-width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: #171717;
  font-size: clamp(24px, 3vw, 34px);
  font-weight: 700;
  line-height: 1.05;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-header-link {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 999px;
  background: #fff;
  color: #181818;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.header-user-btn {
  min-height: 48px;
  padding: 4px 12px 4px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: inset 0 0 0 1px rgba(17, 17, 17, 0.05);
}

.header-user-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  margin-right: 10px;
  border-radius: 999px;
  background: #171717;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}

.header-user-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.2;
}

.header-user-label {
  color: #181818;
  font-size: 14px;
  font-weight: 600;
}

.header-user-role {
  color: #8a8a85;
  font-size: 11px;
}

.admin-header-actions :deep(.t-popup__reference) {
  display: inline-flex;
  align-items: center;
}

.admin-header-actions :deep(.t-button + .t-button) {
  margin-left: 0;
}

.admin-header-actions :deep(.t-button__suffix) {
  margin-left: 8px;
  color: #767671;
}

.admin-header-actions :deep(.t-button) {
  border: none;
}

@media (max-width: 991px) {
  .admin-header-menu {
    padding: 12px 16px 0 12px;
  }

  .admin-header-shell {
    padding: 14px 16px;
  }

  .admin-header-link {
    display: none;
  }

  .header-user-role {
    display: none;
  }
}

@media (max-width: 720px) {
  .admin-header-shell {
    flex-direction: column;
    align-items: stretch;
  }

  .admin-header-actions {
    justify-content: space-between;
  }

  .header-user-btn {
    min-width: 0;
  }

  .header-user-label {
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
