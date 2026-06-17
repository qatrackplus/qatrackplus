<template>
  <div class="form-group" :class="{'has-error': errorUnit}">
    <label class="col-sm-3 control-label">Unit *</label>
    <div class="col-sm-9">
      <select name="fault-unit" v-model="selectedUnit" class="form-control" @change="onUnitChange">
        <option v-for="unit in unitsData" :key="unit.id" :value="unit.id">
          {{ unit.text }}
        </option>
      </select>
      <div v-if="errorUnit" class="help-block error-message">{{ errorUnit }}</div>
    </div>
  </div>

  <div class="form-group" :class="{'has-error': errorModality}">
    <label class="col-sm-3 control-label">Modality</label>
    <div class="col-sm-9">
      <select name="fault-modality" v-model="selectedModality" class="form-control" @change="onModalityChange">
        <option value="">---------</option>
        <option v-for="mod in availableModalities" :key="mod.id" :value="mod.id">
          {{ mod.text }}
        </option>
      </select>
      <div v-if="errorModality" class="help-block error-message">{{ errorModality }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import axios from 'axios';

const props = defineProps({
  initialUnit: [String, Number],
  initialModality: [String, Number],
  unitsData: Array,
  modalitiesData: Array,
  errorUnit: String,
  errorModality: String
});

const emit = defineEmits(['update:unit', 'update:modality']);

const selectedUnit = ref(props.initialUnit || '');
const selectedModality = ref(props.initialModality || '');

const unitInfo = ref({});

// We assume there's a global QAURLs.UNIT_INFO available
const fetchUnitInfo = async () => {
  try {
    const url = (window.QAURLs && window.QAURLs.UNIT_INFO) || '/api/units/info/';
    const res = await axios.get(url, { params: { serviceable_only: true } });
    unitInfo.value = res.data;
    updateAvailableModalities();
  } catch (err) {
    console.error("Failed to fetch unit info", err);
  }
};

const availableModalities = ref([]);

const updateAvailableModalities = () => {
  if (!selectedUnit.value) {
    availableModalities.value = props.modalitiesData || [];
    return;
  }
  
  const unitData = unitInfo.value[selectedUnit.value];
  if (unitData && unitData.modalities) {
    availableModalities.value = (props.modalitiesData || []).filter(m => unitData.modalities.includes(parseInt(m.id)));
  } else {
    availableModalities.value = props.modalitiesData || [];
  }
};

const onUnitChange = () => {
  emit('update:unit', selectedUnit.value);
  updateAvailableModalities();
  selectedModality.value = '';
  emit('update:modality', selectedModality.value);
};

const onModalityChange = () => {
  emit('update:modality', selectedModality.value);
};

onMounted(() => {
  fetchUnitInfo();
  updateAvailableModalities();
  
  watch(() => props.initialUnit, (newVal) => {
    selectedUnit.value = newVal;
    updateAvailableModalities();
  });
  
  watch(() => props.initialModality, (newVal) => {
    selectedModality.value = newVal;
  });
});
</script>
