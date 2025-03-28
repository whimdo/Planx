<template>
    <div style="border: 1px solid #ccc">
      <Toolbar
        style="border-bottom: 1px solid #ccc"
        :editor="editorRef"
        :defaultConfig="toolbarConfig"
        :mode="mode"
      />
      <Editor
        style="height: 200px; overflow-y: hidden;"
        v-model="internalValue"
        :defaultConfig="editorConfig"
        :mode="mode"
        @onCreated="handleCreated"
        @onChange="handleChange"
        @onDestroyed="handleDestroyed"
        @onFocus="handleFocus"
        @onBlur="handleBlur"
        @customAlert="customAlert"
        @customPaste="customPaste"
      />
    </div>
  </template>
  
  <script setup>
  import { ref, shallowRef, onBeforeUnmount, watch } from 'vue'
  import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
  import '@wangeditor/editor/dist/css/style.css'
  
  // 定义 props 和 emits
  defineProps({
    modelValue: {
      type: String,
      default: ''
    },
    toolbarConfig: {
      type: Object,
      default: () => ({})
    },
    editorConfig: {
      type: Object,
      default: () => ({ placeholder: '请输入内容...' })
    },
    mode: {
      type: String,
      default: 'default'
    }
  })
  const emit = defineEmits(['update:modelValue'])
  
  // 编辑器实例
  const editorRef = shallowRef()
  
  // 内部值，用于 v-model 双向绑定
  const internalValue = ref('')
  watch(() => internalValue.value, (newValue) => {
    emit('update:modelValue', newValue)
  })
  watch(() => props.modelValue, (newValue) => {
    if (newValue !== internalValue.value) {
      internalValue.value = newValue
    }
  })
  
  // 编辑器回调函数
  const handleCreated = (editor) => {
    console.log('created', editor)
    editorRef.value = editor
  }
  const handleChange = (editor) => {
    console.log('change:', editor.getHtml())
  }
  const handleDestroyed = (editor) => {
    console.log('destroyed', editor)
  }
  const handleFocus = (editor) => {
    console.log('focus', editor)
  }
  const handleBlur = (editor) => {
    console.log('blur', editor)
  }
  const customAlert = (info, type) => {
    alert(`【自定义提示】${type} - ${info}`)
  }
  const customPaste = (editor, event, callback) => {
    console.log('ClipboardEvent 粘贴事件对象', event)
    editor.insertText('xxx')
    callback(false) // 阻止默认粘贴行为
  }
  
  // 组件销毁时销毁编辑器
  onBeforeUnmount(() => {
    const editor = editorRef.value
    if (editor) editor.destroy()
  })
  
  // 暴露方法给父组件
  defineExpose({
    insertText: (text) => {
      const editor = editorRef.value
      if (editor) editor.insertText(text)
    },
    printHtml: () => {
      const editor = editorRef.value
      if (editor) return editor.getHtml()
    },
    disable: () => {
      const editor = editorRef.value
      if (editor) editor.disable()
    }
  })
  </script>