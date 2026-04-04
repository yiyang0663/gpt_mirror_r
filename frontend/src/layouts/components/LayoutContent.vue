<template>
  <t-layout :class="`${prefix}-layout`">
    <t-tabs
      v-if="settingStore.isUseTabsRouter"
      drag-sort
      theme="card"
      :class="`${prefix}-layout-tabs-nav`"
      :value="$route.path"
      :style="{ position: 'sticky', top: 0, width: '100%' }"
      @change="(value) => handleChangeCurrentTab(value as string)"
      @remove="handleRemove"
      @drag-sort="handleDragend"
    >
      <t-tab-panel
        v-for="(routeItem, index) in tabRouters"
        :key="`${routeItem.path}_${index}`"
        :value="routeItem.path"
        :removable="!routeItem.isHome"
        :draggable="!routeItem.isHome"
      >
        <template #label>
          <t-dropdown
            trigger="context-menu"
            :min-column-width="128"
            :popup-props="{
              overlayClassName: 'route-tabs-dropdown',
              onVisibleChange: (visible: boolean, ctx: PopupVisibleChangeContext) =>
                handleTabMenuClick(visible, ctx, routeItem.path),
              visible: activeTabPath === routeItem.path,
            }"
          >
            <template v-if="!routeItem.isHome">
              {{ renderTitle(routeItem.title) }}
            </template>
            <t-icon v-else name="home" />
            <template #dropdown>
              <t-dropdown-menu>
                <t-dropdown-item @click="() => handleRefresh(routeItem, index)">
                  <t-icon name="refresh" />
                  {{ $t('layout.tagTabs.refresh') }}
                </t-dropdown-item>
                <t-dropdown-item v-if="index > 1" @click="() => handleCloseAhead(routeItem.path, index)">
                  <t-icon name="arrow-left" />
                  {{ $t('layout.tagTabs.closeLeft') }}
                </t-dropdown-item>
                <t-dropdown-item
                  v-if="index < tabRouters.length - 1"
                  @click="() => handleCloseBehind(routeItem.path, index)"
                >
                  <t-icon name="arrow-right" />
                  {{ $t('layout.tagTabs.closeRight') }}
                </t-dropdown-item>
                <t-dropdown-item v-if="tabRouters.length > 2" @click="() => handleCloseOther(routeItem.path, index)">
                  <t-icon name="close-circle" />
                  {{ $t('layout.tagTabs.closeOther') }}
                </t-dropdown-item>
              </t-dropdown-menu>
            </template>
          </t-dropdown>
        </template>
      </t-tab-panel>
    </t-tabs>
    <t-content :class="`${prefix}-content-layout`">
      <div class="admin-workspace">
        <section class="workspace-hero">
          <div class="workspace-copy">
            <p class="workspace-eyebrow">{{ sectionTitle }}</p>
            <h1 class="workspace-title">{{ currentTitle }}</h1>
            <p class="workspace-description">{{ currentDescription }}</p>
          </div>

          <div class="workspace-shortcuts">
            <button
              v-for="shortcut in workspaceShortcuts"
              :key="shortcut.path"
              class="workspace-shortcut"
              :class="{ active: isShortcutActive(shortcut.path) }"
              type="button"
              @click="handleJump(shortcut.path)"
            >
              <span class="workspace-shortcut-kicker">{{ shortcut.kicker }}</span>
              <span class="workspace-shortcut-name">{{ shortcut.label }}</span>
            </button>
          </div>
        </section>

        <div class="workspace-body">
          <l-breadcrumb v-if="settingStore.showBreadcrumb" />
          <l-content />
        </div>
      </div>
    </t-content>
    <t-footer v-if="settingStore.showFooter" :class="`${prefix}-footer-layout`">
      <l-footer />
    </t-footer>
  </t-layout>
</template>

<script setup lang="ts">
import type { PopupVisibleChangeContext } from 'tdesign-vue-next';
import { computed, nextTick, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { prefix } from '@/config/global';
import { useLocale } from '@/locales/useLocale';
import { useSettingStore, useTabsRouterStore } from '@/store';
import type { TRouterInfo, TTabRemoveOptions } from '@/types/interface';

import LBreadcrumb from './Breadcrumb.vue';
import LContent from './Content.vue';
import LFooter from './Footer.vue';

const route = useRoute();
const router = useRouter();

const settingStore = useSettingStore();
const tabsRouterStore = useTabsRouterStore();
const tabRouters = computed(() => tabsRouterStore.tabRouters.filter((route) => route.isAlive || route.isHome));
const activeTabPath = ref('');

const { locale } = useLocale();

const workspaceShortcuts = [
  { path: '/account/user', label: '用户', kicker: 'Accounts' },
  { path: '/account/chatgpt', label: 'ChatGPT', kicker: 'Tokens' },
  { path: '/account/gptcar', label: '号池', kicker: 'Pools' },
  { path: '/system/login-log', label: '登录日志', kicker: 'Audit' },
];

const workspaceDescriptions: Record<string, string> = {
  '/account/user': '管理登录账户、有效期、模型限制与独立会话策略。',
  '/account/chatgpt': '维护 ChatGPT Token 与中转站凭据，快速判断当前可用状态。',
  '/account/gptcar': '整理号池资源和绑定关系，让分配边界保持清晰。',
  '/system/login-log': '核对最近的登录记录与异常访问，便于排查问题。',
};

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
const currentDescription = computed(
  () => workspaceDescriptions[route.path] || '统一维护后台账号、号池和系统状态。',
);

const handleChangeCurrentTab = (path: string) => {
  const { tabRouters } = tabsRouterStore;
  const route = tabRouters.find((i) => i.path === path);
  router.push({ path, query: route.query });
};

const handleRemove = (options: TTabRemoveOptions) => {
  const { tabRouters } = tabsRouterStore;
  const nextRouter = tabRouters[options.index + 1] || tabRouters[options.index - 1];

  tabsRouterStore.subtractCurrentTabRouter({ path: options.value as string, routeIdx: options.index });
  if ((options.value as string) === route.path) router.push({ path: nextRouter.path, query: nextRouter.query });
};

const handleRefresh = (route: TRouterInfo, routeIdx: number) => {
  tabsRouterStore.toggleTabRouterAlive(routeIdx);
  nextTick(() => {
    tabsRouterStore.toggleTabRouterAlive(routeIdx);
    router.replace({ path: route.path, query: route.query });
  });
  activeTabPath.value = null;
};

const handleCloseAhead = (path: string, routeIdx: number) => {
  tabsRouterStore.subtractTabRouterAhead({ path, routeIdx });

  handleOperationEffect('ahead', routeIdx);
};

const handleCloseBehind = (path: string, routeIdx: number) => {
  tabsRouterStore.subtractTabRouterBehind({ path, routeIdx });

  handleOperationEffect('behind', routeIdx);
};

const handleCloseOther = (path: string, routeIdx: number) => {
  tabsRouterStore.subtractTabRouterOther({ path, routeIdx });

  handleOperationEffect('other', routeIdx);
};

const handleOperationEffect = (type: 'other' | 'ahead' | 'behind', routeIndex: number) => {
  const currentPath = router.currentRoute.value.path;
  const { tabRouters } = tabsRouterStore;

  const currentIdx = tabRouters.findIndex((i) => i.path === currentPath);
  const needRefreshRouter =
    (type === 'other' && currentIdx !== routeIndex) ||
    (type === 'ahead' && currentIdx < routeIndex) ||
    (type === 'behind' && currentIdx === -1);
  if (needRefreshRouter) {
    const nextRouteIdx = type === 'behind' ? tabRouters.length - 1 : 1;
    const nextRouter = tabRouters[nextRouteIdx];
    router.push({ path: nextRouter.path, query: nextRouter.query });
  }

  activeTabPath.value = null;
};

const handleTabMenuClick = (visible: boolean, ctx: PopupVisibleChangeContext, path: string) => {
  if (ctx.trigger === 'document') activeTabPath.value = null;
  if (visible) activeTabPath.value = path;
};

const handleDragend = (options: { currentIndex: number; targetIndex: number }) => {
  const { tabRouters } = tabsRouterStore;

  [tabRouters[options.currentIndex], tabRouters[options.targetIndex]] = [
    tabRouters[options.targetIndex],
    tabRouters[options.currentIndex],
  ];
};

const handleJump = (path: string) => {
  if (route.path === path) return;
  router.push(path);
};

const isShortcutActive = (path: string) => route.path === path;
</script>

<style lang="less" scoped>
.admin-workspace {
  max-width: 1320px;
  margin: 0 auto;
}

.workspace-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
  gap: 18px;
  align-items: end;
  padding: 4px 0 28px;
}

.workspace-copy {
  padding: 18px 4px 0;
}

.workspace-eyebrow {
  margin: 0 0 12px;
  color: #7f7f7a;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.workspace-title {
  margin: 0;
  color: #181818;
  font-size: clamp(34px, 4.6vw, 54px);
  font-weight: 700;
  line-height: 1.02;
}

.workspace-description {
  max-width: 560px;
  margin: 16px 0 0;
  color: #6b6b67;
  font-size: 15px;
  line-height: 1.6;
}

.workspace-shortcuts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.workspace-shortcut {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 108px;
  padding: 18px;
  border: 1px solid rgba(17, 17, 17, 0.06);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.74);
  box-shadow:
    0 18px 44px rgba(17, 17, 17, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.82);
  color: #1a1a1a;
  cursor: pointer;
  text-align: left;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease;
}

.workspace-shortcut:hover {
  transform: translateY(-1px);
  border-color: rgba(17, 17, 17, 0.12);
  box-shadow: 0 20px 48px rgba(17, 17, 17, 0.07);
}

.workspace-shortcut.active {
  border-color: rgba(16, 163, 127, 0.18);
  box-shadow:
    0 20px 48px rgba(17, 17, 17, 0.06),
    inset 0 0 0 1px rgba(16, 163, 127, 0.14);
}

.workspace-shortcut-kicker {
  color: #8c8c87;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.workspace-shortcut-name {
  color: #161616;
  font-size: 18px;
  font-weight: 600;
}

.workspace-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@media (max-width: 1080px) {
  .workspace-hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .workspace-shortcuts {
    grid-template-columns: 1fr;
  }

  .workspace-shortcut {
    min-height: 92px;
  }
}
</style>
