<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ msg: string }>()

const fileInput = ref<HTMLInputElement | null>(null)
const folderInput = ref<HTMLInputElement | null>(null)

const selectedFile = ref<string>('')
const selectedFolder = ref<string>('')

function selectFile() {
  fileInput.value?.click()
}

function selectFolder() {
  folderInput.value?.click()
}

function onFileSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0].name
  }
}

function onFolderSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    // The path is not directly available, but we can get the list of files.
    // We'll just show the number of files selected for now.
    selectedFolder.value = `${target.files.length} files selected`
  }
}
</script>

<template>
  <h1>{{ msg }}</h1>

  <div class="card">
    <input type="file" ref="fileInput" @change="onFileSelected" style="display: none" />
    <button type="button" @click="selectFile">File</button>
    <p v-if="selectedFile">Selected File: {{ selectedFile }}</p>

    <input type="file" ref="folderInput" @change="onFolderSelected" style="display: none" webkitdirectory />
    <button type="button" @click="selectFolder">Folder</button>
    <p v-if="selectedFolder">Selected Folder: {{ selectedFolder }}</p>

    <p>
      Edit
      <code>components/HelloWorld.vue</code> to test HMR
    </p>
  </div>

  <p>
    Check out
    <a href="https://vuejs.org/guide/quick-start.html#local" target="_blank"
      >create-vue</a
    >, the official Vue + Vite starter
  </p>
  <p>
    Learn more about IDE Support for Vue in the
    <a
      href="https://vuejs.org/guide/scaling-up/tooling.html#ide-support"
      target="_blank"
      >Vue Docs Scaling up Guide</a
    >.
  </p>
  <p class="read-the-docs">Click on the Vite and Vue logos to learn more</p>
</template>

<style scoped>
.read-the-docs {
  color: #888;
}
</style>
