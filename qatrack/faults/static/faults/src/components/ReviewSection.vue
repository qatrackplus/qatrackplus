<template>
  <fieldset>
    <legend>Reviewers</legend>
    <div v-for="form in reviewForms" :key="form.prefix" class="form-group" :class="{'has-error': getError(form.prefix)}">
      <label class="col-sm-4 control-label">
        {{ form.group_name }} <span v-if="form.required">*</span>
      </label>
      <div class="col-sm-3">
        <input type="text" :name="`${form.prefix}-group`" :value="form.group_name" class="form-control input-sm" readonly="readonly" />
      </div>
      
      <label class="col-sm-2 control-label">Reviewed By</label>
      <div class="col-sm-3">
        <select :name="`${form.prefix}-reviewed_by`" v-model="form.selected" class="form-control input-sm">
          <option value="">---------</option>
          <option v-for="u in form.users" :key="u.id" :value="u.id">{{ u.name }}</option>
        </select>
        
        <div v-if="getError(form.prefix)" class="help-block error-message">
          <p v-for="(err, idx) in getError(form.prefix)" :key="idx">{{ err.message }}</p>
        </div>
      </div>
      
      <!-- hidden field for required if any -->
      <input type="hidden" :name="`${form.prefix}-required`" :value="form.required ? 'True' : 'False'" />
    </div>
  </fieldset>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';

const props = defineProps({
  reviewFormsData: {
    type: Array,
    default: () => []
  },
  reviewErrors: {
    type: Object,
    default: () => ({})
  }
});

const reviewForms = ref([]);

const getError = (prefix) => {
  if (props.reviewErrors && props.reviewErrors[prefix] && props.reviewErrors[prefix].reviewed_by) {
    return props.reviewErrors[prefix].reviewed_by;
  }
  return null;
};

onMounted(() => {
  if (props.reviewFormsData) {
    reviewForms.value = JSON.parse(JSON.stringify(props.reviewFormsData));
  }
});

watch(() => props.reviewFormsData, (newVal) => {
  if (newVal) {
    reviewForms.value = JSON.parse(JSON.stringify(newVal));
  }
});
</script>
