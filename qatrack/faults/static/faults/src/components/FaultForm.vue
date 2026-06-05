<template>
  <div class="box-body">
    <div class="row" v-if="Object.keys(formErrors).length > 0">
      <div class="col-md-12">
        <div class="alert alert-danger">
          <p>Please resolve the errors below and submit again.</p>
        </div>
      </div>
    </div>
    
    <div class="row">
      <div class="col-md-12 form-horizontal">
        <fieldset>
          <legend>Fault Details</legend>
          
          <div class="form-group" :class="{'has-error': getError('occurred')}">
            <label class="col-sm-3 control-label">Occurred On</label>
            <div class="col-sm-9">
              <input type="datetime-local" name="fault-occurred" v-model="form.occurred" class="form-control" />
              <div v-if="getError('occurred')" class="help-block error-message">{{ getError('occurred') }}</div>
            </div>
          </div>

          <UnitModalitySelector 
             :initial-unit="form.unit" 
             :initial-modality="form.modality"
             :units-data="unitsData"
             :modalities-data="modalitiesData"
             :error-unit="getError('unit')"
             :error-modality="getError('modality')"
             @update:unit="form.unit = $event"
             @update:modality="form.modality = $event" />

          <FaultTypeSelector 
             :initial-fault-types="form.fault_types"
             :error="getError('fault_types_field')" />

          <ServiceEventSelector
             :initial-service-events="form.related_service_events"
             :unit-id="form.unit"
             :error="getError('related_service_events')"
             @se-status-updated="handleSeStatusUpdated" />

          <div class="form-group" :class="{'has-error': getError('comment')}">
            <label class="col-sm-3 control-label">Comment</label>
            <div class="col-sm-9">
              <textarea name="fault-comment" v-model="form.comment" class="form-control autosize" rows="3"></textarea>
              <div v-if="getError('comment')" class="help-block error-message">{{ getError('comment') }}</div>
            </div>
          </div>
          
          <AttachmentManager :initial-attachments="form.attachments" />
          
        </fieldset>
      </div>
    </div>
    
    <div class="row" v-if="reviewFormsData && reviewFormsData.length > 0">
      <div class="col-md-12 form-horizontal">
        <ReviewSection :review-forms-data="reviewFormsData" :review-errors="reviewErrors" />
      </div>
    </div>
    
    <div class="row">
      <div class="col-md-12">
        <button class="btn btn-flat btn-primary pull-right" type="submit">
          {{ isEdit ? 'Update Fault' : 'Log Fault' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import UnitModalitySelector from './UnitModalitySelector.vue';
import FaultTypeSelector from './FaultTypeSelector.vue';
import ServiceEventSelector from './ServiceEventSelector.vue';
import AttachmentManager from './AttachmentManager.vue';
import ReviewSection from './ReviewSection.vue';

const form = ref({
  occurred: '',
  unit: null,
  modality: null,
  comment: '',
  fault_types: [],
  related_service_events: [],
  attachments: []
});

const isEdit = ref(false);
const formErrors = ref({});
const reviewErrors = ref({});
const reviewFormsData = ref([]);
const unitsData = ref([]);
const modalitiesData = ref([]);

const handleSeStatusUpdated = (payload) => {
  if (window.se_statuses) {
    window.se_statuses[payload.id] = payload.statusId;
  }
};

const getError = (field) => {
  return formErrors.value[field] ? formErrors.value[field].map(e => e.message).join(', ') : '';
};

onMounted(() => {
  const root = document.getElementById('fault-form-app');
  if (root) {
    if (root.dataset.fault && root.dataset.fault !== 'null') {
      try {
        const f = JSON.parse(root.dataset.fault);
        form.value.unit = f.unit;
        form.value.modality = f.modality;
        form.value.occurred = f.occurred ? f.occurred.substring(0, 16) : '';
        form.value.fault_types = f.fault_types || [];
        form.value.related_service_events = f.related_service_events || [];
        form.value.comment = f.comment || '';
        form.value.attachments = f.attachments || [];
        isEdit.value = true;
      } catch(e) {
        console.error("Error parsing fault data", e);
      }
    }
    if (root.dataset.formErrors) {
      try {
        formErrors.value = JSON.parse(root.dataset.formErrors);
      } catch(e) {}
    }
    if (root.dataset.reviewErrors) {
      try {
        reviewErrors.value = JSON.parse(root.dataset.reviewErrors);
      } catch(e) {}
    }
    if (root.dataset.reviewForms) {
      try {
        reviewFormsData.value = JSON.parse(root.dataset.reviewForms);
      } catch(e) {}
    }
    if (root.dataset.units) {
      try {
        unitsData.value = JSON.parse(root.dataset.units);
      } catch(e) {}
    }
    if (root.dataset.modalities) {
      try {
        modalitiesData.value = JSON.parse(root.dataset.modalities);
      } catch(e) {}
    }
  }
});
</script>
