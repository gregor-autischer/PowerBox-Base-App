<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const entities = ref({})
const searchQuery = ref('')
const isConnected = ref(false)
const activeTab = ref('dashboard')
const rangeValue = ref(50)
const toggleValue = ref(true)
const checkboxValue = ref(true)
const selectValue = ref('option1')
const progress = ref(65)
let ws = null

const filteredEntities = computed(() => {
  const query = searchQuery.value.toLowerCase()
  return Object.values(entities.value)
    .filter(e =>
      e.entity_id.toLowerCase().includes(query) ||
      (e.attributes.friendly_name || '').toLowerCase().includes(query)
    )
    .sort((a, b) => a.entity_id.localeCompare(b.entity_id))
})

const stats = computed(() => {
  const all = Object.values(entities.value)
  return {
    total: all.length,
    lights: all.filter(e => e.entity_id.startsWith('light.')).length,
    switches: all.filter(e => e.entity_id.startsWith('switch.')).length,
    sensors: all.filter(e => e.entity_id.startsWith('sensor.')).length,
  }
})

async function fetchEntities() {
  try {
    const response = await fetch('/api/entities')
    const data = await response.json()
    if (Array.isArray(data)) {
      data.forEach(entity => {
        entities.value[entity.entity_id] = entity
      })
    }
  } catch (error) {
    console.error('Failed to load entities:', error)
  }
}

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${window.location.host}/api/ws`)

  ws.onopen = () => {
    isConnected.value = true
  }

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.event && msg.event.event_type === 'state_changed') {
      const newState = msg.event.data.new_state
      if (newState) {
        entities.value[newState.entity_id] = newState
      }
    }
  }

  ws.onclose = () => {
    isConnected.value = false
    setTimeout(connectWebSocket, 5000)
  }

  ws.onerror = (err) => {
    console.error('WebSocket error:', err)
  }
}

onMounted(() => {
  fetchEntities()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<template>
  <div class="min-h-screen bg-base-200" data-theme="powerhaus">
    <!-- Navbar -->
    <div class="navbar bg-base-100 shadow-lg border-b border-base-300">
      <div class="navbar-start">
        <div class="dropdown">
          <div tabindex="0" role="button" class="btn btn-ghost lg:hidden">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16" />
            </svg>
          </div>
          <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
            <li><a @click="activeTab = 'dashboard'" :class="{ 'active': activeTab === 'dashboard' }">Dashboard</a></li>
            <li><a @click="activeTab = 'entities'" :class="{ 'active': activeTab === 'entities' }">Entities</a></li>
            <li><a @click="activeTab = 'components'" :class="{ 'active': activeTab === 'components' }">Components</a></li>
          </ul>
        </div>
        <a class="btn btn-ghost text-xl font-bold">
          <span class="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">PowerHaus</span>
        </a>
      </div>
      <div class="navbar-center hidden lg:flex">
        <ul class="menu menu-horizontal px-1">
          <li><a @click="activeTab = 'dashboard'" :class="{ 'bg-primary text-primary-content': activeTab === 'dashboard' }">Dashboard</a></li>
          <li><a @click="activeTab = 'entities'" :class="{ 'bg-primary text-primary-content': activeTab === 'entities' }">Entities</a></li>
          <li><a @click="activeTab = 'components'" :class="{ 'bg-primary text-primary-content': activeTab === 'components' }">Components</a></li>
        </ul>
      </div>
      <div class="navbar-end gap-2">
        <div class="badge badge-lg gap-2" :class="isConnected ? 'badge-success' : 'badge-warning'">
          <span class="w-2 h-2 rounded-full animate-pulse" :class="isConnected ? 'bg-white' : 'bg-white'"></span>
          {{ isConnected ? 'Connected' : 'Connecting...' }}
        </div>
        <div class="dropdown dropdown-end">
          <div tabindex="0" role="button" class="btn btn-ghost btn-circle avatar placeholder">
            <div class="bg-primary text-primary-content rounded-full w-10">
              <span>PH</span>
            </div>
          </div>
          <ul tabindex="0" class="mt-3 z-[1] p-2 shadow menu menu-sm dropdown-content bg-base-100 rounded-box w-52">
            <li><a>Settings</a></li>
            <li><a>Documentation</a></li>
          </ul>
        </div>
      </div>
    </div>

    <div class="container mx-auto p-6">
      <!-- Dashboard Tab -->
      <div v-if="activeTab === 'dashboard'" class="space-y-6">
        <!-- Hero Section -->
        <div class="hero bg-gradient-to-r from-primary to-secondary rounded-2xl text-primary-content">
          <div class="hero-content text-center py-12">
            <div class="max-w-md">
              <h1 class="text-5xl font-bold">PowerHaus</h1>
              <p class="py-6">Your intelligent Home Assistant add-on for seamless smart home automation and monitoring.</p>
              <button class="btn btn-neutral">Get Started</button>
            </div>
          </div>
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="stat bg-base-100 rounded-xl shadow-lg border border-base-300">
            <div class="stat-figure text-primary">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-8 h-8 stroke-current">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
              </svg>
            </div>
            <div class="stat-title">Total Entities</div>
            <div class="stat-value text-primary">{{ stats.total }}</div>
            <div class="stat-desc">All registered devices</div>
          </div>

          <div class="stat bg-base-100 rounded-xl shadow-lg border border-base-300">
            <div class="stat-figure text-secondary">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-8 h-8 stroke-current">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
              </svg>
            </div>
            <div class="stat-title">Lights</div>
            <div class="stat-value text-secondary">{{ stats.lights }}</div>
            <div class="stat-desc">Controllable lights</div>
          </div>

          <div class="stat bg-base-100 rounded-xl shadow-lg border border-base-300">
            <div class="stat-figure text-accent">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-8 h-8 stroke-current">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
            </div>
            <div class="stat-title">Switches</div>
            <div class="stat-value text-accent">{{ stats.switches }}</div>
            <div class="stat-desc">Active switches</div>
          </div>

          <div class="stat bg-base-100 rounded-xl shadow-lg border border-base-300">
            <div class="stat-figure text-info">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-8 h-8 stroke-current">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
            </div>
            <div class="stat-title">Sensors</div>
            <div class="stat-value text-info">{{ stats.sensors }}</div>
            <div class="stat-desc">Monitoring sensors</div>
          </div>
        </div>

        <!-- Info Cards Row -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Alert Examples -->
          <div class="card bg-base-100 shadow-lg border border-base-300">
            <div class="card-body">
              <h2 class="card-title text-primary">System Alerts</h2>
              <div class="space-y-3">
                <div role="alert" class="alert alert-info">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                  <span>Publishing entity: <code class="font-mono bg-base-200 px-2 py-1 rounded">sensor.powerhaus</code></span>
                </div>
                <div role="alert" class="alert alert-success">
                  <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>WebSocket connection established!</span>
                </div>
                <div role="alert" class="alert alert-warning">
                  <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <span>State toggles between 0 and 1 every 5 seconds</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Progress & Metrics -->
          <div class="card bg-base-100 shadow-lg border border-base-300">
            <div class="card-body">
              <h2 class="card-title text-secondary">System Metrics</h2>
              <div class="space-y-4">
                <div>
                  <div class="flex justify-between mb-1">
                    <span class="text-sm font-medium">CPU Usage</span>
                    <span class="text-sm text-base-content/60">{{ progress }}%</span>
                  </div>
                  <progress class="progress progress-primary w-full" :value="progress" max="100"></progress>
                </div>
                <div>
                  <div class="flex justify-between mb-1">
                    <span class="text-sm font-medium">Memory</span>
                    <span class="text-sm text-base-content/60">42%</span>
                  </div>
                  <progress class="progress progress-secondary w-full" value="42" max="100"></progress>
                </div>
                <div>
                  <div class="flex justify-between mb-1">
                    <span class="text-sm font-medium">Storage</span>
                    <span class="text-sm text-base-content/60">78%</span>
                  </div>
                  <progress class="progress progress-accent w-full" value="78" max="100"></progress>
                </div>
                <div class="flex gap-2 mt-4">
                  <div class="radial-progress text-primary" style="--value:70; --size:4rem;" role="progressbar">70%</div>
                  <div class="radial-progress text-secondary" style="--value:85; --size:4rem;" role="progressbar">85%</div>
                  <div class="radial-progress text-accent" style="--value:55; --size:4rem;" role="progressbar">55%</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Timeline -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-primary">Recent Activity</h2>
            <ul class="timeline timeline-vertical lg:timeline-horizontal">
              <li>
                <div class="timeline-start timeline-box bg-primary text-primary-content">Add-on Started</div>
                <div class="timeline-middle">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-primary">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
                  </svg>
                </div>
                <hr class="bg-primary"/>
              </li>
              <li>
                <hr class="bg-primary"/>
                <div class="timeline-middle">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-secondary">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="timeline-end timeline-box bg-secondary text-secondary-content">Connected to HA</div>
                <hr class="bg-secondary"/>
              </li>
              <li>
                <hr class="bg-accent"/>
                <div class="timeline-start timeline-box bg-accent text-accent-content">Entities Loaded</div>
                <div class="timeline-middle">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-accent">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
                  </svg>
                </div>
                <hr class="bg-info"/>
              </li>
              <li>
                <hr class="bg-info"/>
                <div class="timeline-middle">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-info">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="timeline-end timeline-box bg-info text-info-content">Monitoring Active</div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Entities Tab -->
      <div v-if="activeTab === 'entities'" class="space-y-6">
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
              <h2 class="card-title text-primary">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                Home Assistant Entities
              </h2>
              <div class="badge badge-lg badge-outline badge-primary">{{ filteredEntities.length }} entities</div>
            </div>

            <!-- Search with Join -->
            <div class="join w-full mb-6">
              <div class="join-item bg-base-200 flex items-center px-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-base-content/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Search entities by ID or name..."
                class="input input-bordered join-item w-full focus:outline-primary"
              />
              <button class="btn btn-primary join-item">Search</button>
            </div>

            <!-- Entities Table -->
            <div class="overflow-x-auto rounded-lg border border-base-300">
              <table class="table table-zebra">
                <thead class="bg-base-200">
                  <tr>
                    <th class="font-semibold">Entity ID</th>
                    <th class="font-semibold">State</th>
                    <th class="font-semibold">Friendly Name</th>
                    <th class="font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="entity in filteredEntities" :key="entity.entity_id" class="hover">
                    <td>
                      <div class="flex items-center gap-2">
                        <div class="avatar placeholder">
                          <div class="bg-primary text-primary-content rounded-lg w-8">
                            <span class="text-xs">{{ entity.entity_id.split('.')[0].charAt(0).toUpperCase() }}</span>
                          </div>
                        </div>
                        <span class="font-mono text-sm">{{ entity.entity_id }}</span>
                      </div>
                    </td>
                    <td>
                      <span class="badge" :class="{
                        'badge-success': entity.state === 'on',
                        'badge-error': entity.state === 'off',
                        'badge-primary': entity.state !== 'on' && entity.state !== 'off'
                      }">{{ entity.state }}</span>
                    </td>
                    <td>{{ entity.attributes.friendly_name || '-' }}</td>
                    <td>
                      <div class="flex gap-2">
                        <button class="btn btn-xs btn-ghost btn-circle">
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </button>
                        <button class="btn btn-xs btn-ghost btn-circle">
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                  <tr v-if="filteredEntities.length === 0">
                    <td colspan="4" class="text-center py-8">
                      <div class="flex flex-col items-center gap-2 text-base-content/50">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>No entities found</span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- Components Tab -->
      <div v-if="activeTab === 'components'" class="space-y-6">
        <!-- Buttons Section -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-primary mb-4">Buttons</h2>
            <div class="flex flex-wrap gap-2">
              <button class="btn btn-primary">Primary</button>
              <button class="btn btn-secondary">Secondary</button>
              <button class="btn btn-accent">Accent</button>
              <button class="btn btn-info">Info</button>
              <button class="btn btn-success">Success</button>
              <button class="btn btn-warning">Warning</button>
              <button class="btn btn-error">Error</button>
              <button class="btn btn-ghost">Ghost</button>
              <button class="btn btn-link">Link</button>
              <button class="btn btn-outline btn-primary">Outline</button>
            </div>
            <div class="divider"></div>
            <div class="flex flex-wrap gap-2">
              <button class="btn btn-primary btn-xs">Tiny</button>
              <button class="btn btn-primary btn-sm">Small</button>
              <button class="btn btn-primary">Normal</button>
              <button class="btn btn-primary btn-lg">Large</button>
            </div>
            <div class="divider"></div>
            <div class="flex flex-wrap gap-2">
              <button class="btn btn-primary loading">Loading</button>
              <button class="btn btn-square btn-primary">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              <button class="btn btn-circle btn-secondary">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Form Controls -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-secondary mb-4">Form Controls</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Input Group -->
              <div class="form-control w-full">
                <label class="label">
                  <span class="label-text font-medium">Text Input</span>
                  <span class="label-text-alt text-base-content/50">Required</span>
                </label>
                <input type="text" placeholder="Enter text..." class="input input-bordered input-primary w-full" />
                <label class="label">
                  <span class="label-text-alt text-base-content/50">Helper text goes here</span>
                </label>
              </div>

              <!-- Select -->
              <div class="form-control w-full">
                <label class="label">
                  <span class="label-text font-medium">Select Option</span>
                </label>
                <select v-model="selectValue" class="select select-bordered select-secondary w-full">
                  <option value="option1">Option 1</option>
                  <option value="option2">Option 2</option>
                  <option value="option3">Option 3</option>
                </select>
              </div>

              <!-- Textarea -->
              <div class="form-control w-full md:col-span-2">
                <label class="label">
                  <span class="label-text font-medium">Message</span>
                </label>
                <textarea class="textarea textarea-bordered textarea-accent h-24" placeholder="Enter your message..."></textarea>
              </div>

              <!-- Toggle & Checkbox -->
              <div class="space-y-4">
                <div class="form-control">
                  <label class="label cursor-pointer justify-start gap-4">
                    <input type="checkbox" v-model="toggleValue" class="toggle toggle-primary" />
                    <span class="label-text">Enable notifications</span>
                  </label>
                </div>
                <div class="form-control">
                  <label class="label cursor-pointer justify-start gap-4">
                    <input type="checkbox" v-model="checkboxValue" class="checkbox checkbox-secondary" />
                    <span class="label-text">I agree to terms</span>
                  </label>
                </div>
              </div>

              <!-- Radio -->
              <div class="space-y-2">
                <div class="form-control">
                  <label class="label cursor-pointer justify-start gap-4">
                    <input type="radio" name="radio-example" class="radio radio-primary" checked />
                    <span class="label-text">Option A</span>
                  </label>
                </div>
                <div class="form-control">
                  <label class="label cursor-pointer justify-start gap-4">
                    <input type="radio" name="radio-example" class="radio radio-primary" />
                    <span class="label-text">Option B</span>
                  </label>
                </div>
              </div>

              <!-- Range -->
              <div class="form-control w-full md:col-span-2">
                <label class="label">
                  <span class="label-text font-medium">Volume: {{ rangeValue }}%</span>
                </label>
                <input type="range" v-model="rangeValue" min="0" max="100" class="range range-primary" />
                <div class="w-full flex justify-between text-xs px-2 text-base-content/50">
                  <span>0</span>
                  <span>25</span>
                  <span>50</span>
                  <span>75</span>
                  <span>100</span>
                </div>
              </div>

              <!-- Rating -->
              <div class="form-control">
                <label class="label">
                  <span class="label-text font-medium">Rating</span>
                </label>
                <div class="rating rating-lg">
                  <input type="radio" name="rating-demo" class="mask mask-star-2 bg-primary" />
                  <input type="radio" name="rating-demo" class="mask mask-star-2 bg-primary" />
                  <input type="radio" name="rating-demo" class="mask mask-star-2 bg-primary" checked />
                  <input type="radio" name="rating-demo" class="mask mask-star-2 bg-primary" />
                  <input type="radio" name="rating-demo" class="mask mask-star-2 bg-primary" />
                </div>
              </div>

              <!-- File Input -->
              <div class="form-control w-full">
                <label class="label">
                  <span class="label-text font-medium">Upload File</span>
                </label>
                <input type="file" class="file-input file-input-bordered file-input-primary w-full" />
              </div>
            </div>
          </div>
        </div>

        <!-- Badges & Indicators -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-accent mb-4">Badges & Indicators</h2>
            <div class="flex flex-wrap gap-2 mb-4">
              <span class="badge">Default</span>
              <span class="badge badge-primary">Primary</span>
              <span class="badge badge-secondary">Secondary</span>
              <span class="badge badge-accent">Accent</span>
              <span class="badge badge-info">Info</span>
              <span class="badge badge-success">Success</span>
              <span class="badge badge-warning">Warning</span>
              <span class="badge badge-error">Error</span>
            </div>
            <div class="flex flex-wrap gap-2 mb-4">
              <span class="badge badge-outline badge-primary">Outline</span>
              <span class="badge badge-lg badge-secondary">Large</span>
              <span class="badge badge-sm badge-accent">Small</span>
              <span class="badge badge-xs badge-info">Tiny</span>
            </div>
            <div class="divider"></div>
            <div class="flex flex-wrap gap-4">
              <div class="indicator">
                <span class="indicator-item badge badge-primary">99+</span>
                <button class="btn">Inbox</button>
              </div>
              <div class="indicator">
                <span class="indicator-item indicator-bottom badge badge-secondary">NEW</span>
                <button class="btn">Messages</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Tabs Example -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-primary mb-4">Tabs</h2>
            <div role="tablist" class="tabs tabs-boxed bg-base-200">
              <a role="tab" class="tab tab-active">Tab 1</a>
              <a role="tab" class="tab">Tab 2</a>
              <a role="tab" class="tab">Tab 3</a>
            </div>
            <div class="divider"></div>
            <div role="tablist" class="tabs tabs-bordered">
              <a role="tab" class="tab">Tab 1</a>
              <a role="tab" class="tab tab-active">Tab 2</a>
              <a role="tab" class="tab">Tab 3</a>
            </div>
            <div class="divider"></div>
            <div role="tablist" class="tabs tabs-lifted">
              <a role="tab" class="tab">Tab 1</a>
              <a role="tab" class="tab">Tab 2</a>
              <a role="tab" class="tab tab-active">Tab 3</a>
            </div>
          </div>
        </div>

        <!-- Steps -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-secondary mb-4">Steps</h2>
            <ul class="steps w-full">
              <li class="step step-primary">Register</li>
              <li class="step step-primary">Choose plan</li>
              <li class="step">Purchase</li>
              <li class="step">Receive Product</li>
            </ul>
          </div>
        </div>

        <!-- Collapse / Accordion -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-accent mb-4">Accordion</h2>
            <div class="join join-vertical w-full">
              <div class="collapse collapse-arrow join-item border border-base-300">
                <input type="radio" name="accordion" checked />
                <div class="collapse-title text-lg font-medium">What is PowerHaus?</div>
                <div class="collapse-content">
                  <p>PowerHaus is a powerful Home Assistant add-on that provides advanced monitoring and control capabilities for your smart home devices.</p>
                </div>
              </div>
              <div class="collapse collapse-arrow join-item border border-base-300">
                <input type="radio" name="accordion" />
                <div class="collapse-title text-lg font-medium">How do I get started?</div>
                <div class="collapse-content">
                  <p>Simply install the add-on from the Home Assistant add-on store, configure your preferences, and you're ready to go!</p>
                </div>
              </div>
              <div class="collapse collapse-arrow join-item border border-base-300">
                <input type="radio" name="accordion" />
                <div class="collapse-title text-lg font-medium">Is it free to use?</div>
                <div class="collapse-content">
                  <p>Yes! PowerHaus is completely free and open source. Contributions are always welcome.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Avatars & Masks -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-info mb-4">Avatars</h2>
            <div class="flex flex-wrap gap-4 items-center">
              <div class="avatar placeholder">
                <div class="bg-primary text-primary-content rounded-full w-12">
                  <span>PH</span>
                </div>
              </div>
              <div class="avatar placeholder">
                <div class="bg-secondary text-secondary-content rounded-full w-12">
                  <span>HA</span>
                </div>
              </div>
              <div class="avatar placeholder online">
                <div class="bg-accent text-accent-content rounded-full w-12">
                  <span>ON</span>
                </div>
              </div>
              <div class="avatar placeholder offline">
                <div class="bg-neutral text-neutral-content rounded-full w-12">
                  <span>OF</span>
                </div>
              </div>
              <div class="avatar-group -space-x-6 rtl:space-x-reverse">
                <div class="avatar placeholder">
                  <div class="w-12 bg-primary text-primary-content">
                    <span>A</span>
                  </div>
                </div>
                <div class="avatar placeholder">
                  <div class="w-12 bg-secondary text-secondary-content">
                    <span>B</span>
                  </div>
                </div>
                <div class="avatar placeholder">
                  <div class="w-12 bg-accent text-accent-content">
                    <span>C</span>
                  </div>
                </div>
                <div class="avatar placeholder">
                  <div class="w-12 bg-neutral text-neutral-content">
                    <span>+5</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Kbd & Code -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-primary mb-4">Keyboard & Code</h2>
            <div class="flex flex-wrap gap-2 mb-4">
              <kbd class="kbd">A</kbd>
              <kbd class="kbd">B</kbd>
              <kbd class="kbd">C</kbd>
            </div>
            <p class="mb-4">Press <kbd class="kbd kbd-sm">Ctrl</kbd> + <kbd class="kbd kbd-sm">C</kbd> to copy</p>
            <div class="mockup-code">
              <pre data-prefix="$"><code>npm install powerhaus</code></pre>
              <pre data-prefix=">" class="text-warning"><code>installing...</code></pre>
              <pre data-prefix=">" class="text-success"><code>Done!</code></pre>
            </div>
          </div>
        </div>

        <!-- Loading States -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-secondary mb-4">Loading States</h2>
            <div class="flex flex-wrap gap-4 items-center">
              <span class="loading loading-spinner loading-lg text-primary"></span>
              <span class="loading loading-dots loading-lg text-secondary"></span>
              <span class="loading loading-ring loading-lg text-accent"></span>
              <span class="loading loading-ball loading-lg text-info"></span>
              <span class="loading loading-bars loading-lg text-success"></span>
              <span class="loading loading-infinity loading-lg text-warning"></span>
            </div>
          </div>
        </div>

        <!-- Tooltip -->
        <div class="card bg-base-100 shadow-lg border border-base-300">
          <div class="card-body">
            <h2 class="card-title text-accent mb-4">Tooltips</h2>
            <div class="flex flex-wrap gap-4">
              <div class="tooltip" data-tip="Hello from top!">
                <button class="btn btn-primary">Top</button>
              </div>
              <div class="tooltip tooltip-bottom" data-tip="Hello from bottom!">
                <button class="btn btn-secondary">Bottom</button>
              </div>
              <div class="tooltip tooltip-left" data-tip="Hello from left!">
                <button class="btn btn-accent">Left</button>
              </div>
              <div class="tooltip tooltip-right" data-tip="Hello from right!">
                <button class="btn btn-info">Right</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <footer class="footer footer-center p-10 bg-base-100 text-base-content border-t border-base-300 mt-10">
      <aside>
        <div class="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent font-bold text-2xl mb-2">PowerHaus</div>
        <p>Home Assistant Add-on for Smart Home Monitoring</p>
        <p>Copyright 2024 - All rights reserved</p>
      </aside>
      <nav>
        <div class="grid grid-flow-col gap-4">
          <a class="btn btn-ghost btn-circle">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" class="fill-current">
              <path d="M24 4.557c-.883.392-1.832.656-2.828.775 1.017-.609 1.798-1.574 2.165-2.724-.951.564-2.005.974-3.127 1.195-.897-.957-2.178-1.555-3.594-1.555-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.397 4.768 2.212 7.548 2.212 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z"></path>
            </svg>
          </a>
          <a class="btn btn-ghost btn-circle">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" class="fill-current">
              <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"></path>
            </svg>
          </a>
          <a class="btn btn-ghost btn-circle">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" class="fill-current">
              <path d="M9 8h-3v4h3v12h5v-12h3.642l.358-4h-4v-1.667c0-.955.192-1.333 1.115-1.333h2.885v-5h-3.808c-3.596 0-5.192 1.583-5.192 4.615v3.385z"></path>
            </svg>
          </a>
        </div>
      </nav>
    </footer>
  </div>
</template>
