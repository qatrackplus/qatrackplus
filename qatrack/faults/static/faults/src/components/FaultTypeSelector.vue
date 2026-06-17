<template>
  <div class="form-group" :class="{'has-error': error}">
    <label class="col-sm-3 control-label">Fault Type *</label>
    <div class="col-sm-9">
      <!-- Hidden inputs for form submission -->
      <select name="fault-fault_types_field" multiple style="display:none;">
         <option v-for="ft in selected" :key="ft.id" :value="ft.id" selected></option>
      </select>
      
      <div class="vue-select-container" style="position: relative;">
         <div class="selected-items" style="margin-bottom: 5px;">
            <span v-for="ft in selected" :key="ft.id" class="label label-primary margin-r-5" style="display:inline-block; margin-bottom:5px;">
               {{ ft.text }} 
               <i class="fa fa-times" @click="removeSelected(ft)" style="cursor:pointer; margin-left: 5px;"></i>
            </span>
         </div>
         <input type="text" v-model="searchQuery" class="form-control" placeholder="Search or enter new fault type code..." @input="debouncedSearch" @focus="showDropdown = true" @blur="hideDropdownDelay" />
         <ul class="dropdown-menu" style="display:block; width: 100%; max-height: 200px; overflow-y: auto; position: absolute; z-index: 1000;" v-show="showDropdown && results.length">
            <li v-for="res in results" :key="res.id">
               <a href="#" @click.prevent="selectResult(res)">
                  {{ res.text }} <span v-if="res.description">- {{ res.description }}</span>
               </a>
            </li>
         </ul>
      </div>
      
      <div v-if="error" class="help-block error-message">{{ error }}</div>
      
      <dl class="dl-horizontal margin-top-10" id="fault-type-descriptions">
        <template v-for="ft in selected" :key="ft.id">
          <dt>{{ ft.code }}</dt>
          <dd><em v-if="!ft.description">No Description Available</em><span v-else>{{ ft.description }}</span></dd>
        </template>
      </dl>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import axios from 'axios';

const props = defineProps({
  initialFaultTypes: Array,
  error: String
});

const selected = ref([]);
const searchQuery = ref('');
const results = ref([]);
const showDropdown = ref(false);
let searchTimeout = null;

const fetchInitialTypes = async () => {
  if (!props.initialFaultTypes || props.initialFaultTypes.length === 0) return;
  
  for (const ftCode of props.initialFaultTypes) {
    try {
      const url = (window.QAURLs && window.QAURLs.FAULT_TYPE_AUTOCOMPLETE) || '/faults/type/autocomplete.json';
      const res = await axios.get(url, { params: { q: ftCode, suggestions: 1 } });
      if (res.data && res.data.results && res.data.results.length > 0) {
        selected.value.push(res.data.results[0]);
      }
    } catch (e) {
      console.error(e);
    }
  }
};

const debouncedSearch = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(search, 300);
};

const search = async () => {
  if (!searchQuery.value) {
    results.value = [];
    return;
  }
  showDropdown.value = true;
  try {
    const url = (window.QAURLs && window.QAURLs.FAULT_TYPE_AUTOCOMPLETE) || '/faults/type/autocomplete.json';
    const res = await axios.get(url, { params: { q: searchQuery.value, suggestions: 1 } });
    results.value = res.data.results || [];
  } catch(e) {
    console.error(e);
  }
};

const selectResult = (res) => {
  if (!selected.value.find(s => s.id === res.id)) {
    selected.value.push(res);
  }
  searchQuery.value = '';
  results.value = [];
  showDropdown.value = false;
};

const removeSelected = (res) => {
  selected.value = selected.value.filter(s => s.id !== res.id);
};

const hideDropdownDelay = () => {
  setTimeout(() => {
    showDropdown.value = false;
  }, 200);
};

onMounted(() => {
  fetchInitialTypes();
});
</script>
