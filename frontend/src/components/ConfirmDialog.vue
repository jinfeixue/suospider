<template>
  <div class="confirm-dialog">
    <el-dialog
      v-model="visible"
      :title="title"
      :width="width"
      :close-on-click-modal="false"
      @close="handleClose"
    >
      <div class="confirm-body">
        <el-icon :size="48" :color="iconColor" style="margin-bottom: 16px">
          <component :is="icon" />
        </el-icon>
        <p class="confirm-message">{{ message }}</p>
        <p v-if="description" class="confirm-description">{{ description }}</p>
      </div>
      <template #footer>
        <el-button @click="handleCancel">{{ cancelText }}</el-button>
        <el-button :type="confirmType" :loading="loading" @click="handleConfirm">
          {{ confirmText }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  message: { type: String, required: true },
  description: { type: String, default: '' },
  type: { type: String, default: 'warning' }, // warning, danger, info
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  width: { type: String, default: '400px' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const icon = computed(() => ({
  warning: 'WarningFilled',
  danger: 'CircleCloseFilled',
  info: 'InfoFilled',
}[props.type] || 'WarningFilled'))

const iconColor = computed(() => ({
  warning: '#e6a23c',
  danger: '#f56c6c',
  info: '#409eff',
}[props.type] || '#e6a23c'))

const confirmType = computed(() => ({
  warning: 'warning',
  danger: 'danger',
  info: 'primary',
}[props.type] || 'primary'))

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  emit('cancel')
  visible.value = false
}

function handleClose() {
  emit('cancel')
}
</script>

<style scoped>
.confirm-body {
  text-align: center;
  padding: 20px 0;
}
.confirm-message {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 8px;
}
.confirm-description {
  font-size: 14px;
  color: #999;
  margin: 0;
}
</style>
