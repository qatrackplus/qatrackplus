<template>
  <div class="form-group" :class="{'has-error': error}">
    <label class="col-sm-3 control-label">Related Service Events</label>
    <div class="col-sm-9">
      <!-- Hidden inputs for form submission -->
      <select name="fault-related_service_events" multiple style="display:none;">
         <option v-for="se in selected" :key="se.id" :value="se.id" selected></option>
      </select>
      
      <div class="vue-select-container" style="position: relative;">
         <div class="selected-items" style="margin-bottom: 5px;">
            <span v-for="se in selected" :key="se.id" class="label margin-r-5" :style="getBadgeStyle(se.status_id)" style="display:inline-block; margin-bottom:5px; padding:5px;">
               <span :title="se.title">{{ se.text }} ({{ se.date }})</span>
               <i class="fa fa-times" @click="removeSelected(se)" style="cursor:pointer; margin-left: 5px;"></i>
            </span>
         </div>
         <input type="text" v-model="searchQuery" class="form-control" placeholder="Search service events..." @input="debouncedSearch" @focus="showDropdown = true" @blur="hideDropdownDelay" :disabled="!unitId" />
         <ul class="dropdown-menu" style="display:block; width: 100%; max-height: 250px; overflow-y: auto; position: absolute; z-index: 1000;" v-show="showDropdown && results.length">
            <li v-for="res in results" :key="res.id" style="border-bottom: 1px solid #eee;">
               <a href="#" @click.prevent="selectResult(res)" style="padding: 10px;">
                  <div class="clearfix">
                     <span>{{ res.text }} ({{ res.date }}): <em :title="res.title">{{ truncate(res.title) }}</em></span>
                     <span class="label pull-right" :style="getBadgeStyleBorder(res.status_id)">{{ res.status }}</span>
                  </div>
               </a>
            </li>
         </ul>
      </div>
      
      <div v-if="error" class="help-block error-message">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import axios from 'axios';

const props = defineProps({
  initialServiceEvents: Array,
  unitId: [String, Number],
  error: String
});

const emit = defineEmits(['se-status-updated']);

const selected = ref([]);
const searchQuery = ref('');
const results = ref([]);
const showDropdown = ref(false);
let searchTimeout = null;

const isLightColor = (color) => {
  if (!color) return false;
  let hex = color.replace('#', '');
  if (hex.length === 3) {
    hex = hex.split('').map(c => c + c).join('');
  }
  if (hex.length !== 6) return false;

  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);
  
  const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
  return yiq >= 128;
};

const getBadgeStyle = (statusId) => {
  const color = (window.status_colours_dict && window.status_colours_dict[statusId]) || '#777';
  return {
    backgroundColor: color,
    borderColor: color,
    color: isLightColor(color) ? '#000' : '#fff'
  };
};

const getBadgeStyleBorder = (statusId) => {
  const color = (window.status_colours_dict && window.status_colours_dict[statusId]) || '#777';
  return {
    backgroundColor: 'transparent',
    borderColor: color,
    borderWidth: '1px',
    borderStyle: 'solid',
    color: color
  };
};

const truncate = (text) => {
  if (!text) return '';
  return text.length > 80 ? text.slice(0, 80) + '...' : text;
};

// We don't have an endpoint to fetch a single SE by ID, but since they are initially loaded on edit,
// we'd need their full data. Let's assume we can't easily fetch their text without the search endpoint.
// Wait, when editing, QATrack+ prepopulates the Select2 with HTML options.
// In our Vue app, we only get their IDs in `initialServiceEvents`. We need their text/status.
// But wait! We injected `data-se-statuses` earlier.
// `se_statuses` = { 1: 3, 2: 4 } (ID to status_id). But we don't have their title/date!
// If we can't get them, we can at least show their IDs and statuses. 
const populateInitial = () => {
  if (!props.initialServiceEvents) return;
  const seStatuses = window.se_statuses || {};
  for (const seId of props.initialServiceEvents) {
    if (!selected.value.find(s => String(s.id) === String(seId))) {
      selected.value.push({
        id: String(seId),
        text: String(seId),
        date: '',
        title: '',
        status: '',
        status_id: seStatuses[String(seId)] || seStatuses[Number(seId)]
      });
    }
  }
};

const debouncedSearch = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(search, 300);
};

const search = async () => {
  if (!props.unitId) return;
  showDropdown.value = true;
  try {
    const url = (window.QAURLs && window.QAURLs.SE_SEARCHER) || '/service_log/se_searcher/';
    const res = await axios.get(url, { params: { q: searchQuery.value, unit_id: props.unitId } });
    
    // Parse QATrack+ specific JSON structure
    const data = res.data;
    const parsedResults = [];
    for (const i in data.service_events) {
      const seArray = data.service_events[i];
      // [se_id, se_status_id, se_problem_description, se_date, se_status_name]
      // Try to parse date, fallback to raw string
      let seDateStr = seArray[3];
      if (window.moment && window.siteConfig) {
        seDateStr = window.moment(seArray[3]).format(window.siteConfig.MOMENT_DATETIME_FMT);
      }
      parsedResults.push({
        id: String(seArray[0]),
        status_id: seArray[1],
        title: seArray[2],
        date: seDateStr,
        status: seArray[4],
        text: String(seArray[0])
      });
      // Emit event instead of mutating global state directly
      emit('se-status-updated', { id: String(seArray[0]), statusId: seArray[1] });
    }
    results.value = parsedResults;
  } catch(e) {
    console.error(e);
  }
};

const selectResult = (res) => {
  if (!selected.value.find(s => String(s.id) === String(res.id))) {
    // replace dummy entry if we select it and it didn't have full info
    const existingIdx = selected.value.findIndex(s => String(s.id) === String(res.id));
    if (existingIdx >= 0) {
      selected.value[existingIdx] = res;
    } else {
      selected.value.push(res);
    }
  }
  searchQuery.value = '';
  results.value = [];
  showDropdown.value = false;
};

const removeSelected = (res) => {
  selected.value = selected.value.filter(s => String(s.id) !== String(res.id));
};

const hideDropdownDelay = () => {
  setTimeout(() => {
    showDropdown.value = false;
  }, 200);
};

watch(() => props.unitId, (newVal, oldVal) => {
  if (newVal !== oldVal && oldVal !== undefined && oldVal !== null && oldVal !== '') {
    selected.value = [];
  }
});

onMounted(() => {
  populateInitial();
});
</script>
