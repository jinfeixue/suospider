<template>
  <div class="empty-state">
    <el-empty :image-size="imageSize">
      <template #image>
        <el-icon :size="64" color="#c0c4cc">
          <component :is="icon" />
        </el-icon>
      </template>
      <template #description>
        <p class="empty-title">{{ title }}</p>
        <p v-if="description" class="empty-desc">{{ description }}</p>
      </template>
      <slot name="action" />
    </el-empty>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '暂无数据' },
  description: { type: String, default: '' },
  icon: { type: String, default: 'Document' },
  imageSize: { type: Number, default: 120 },
})
</script>

<style scoped>
.empty-state {
  padding: 60px 0;
}
.empty-title {
  font-size: 16px;
  color: #606266;
  margin: 0 0 8px;
}
.empty-desc {
  font-size: 14px;
  color: #909399;
  margin: 0;
}
</style>
