<template>
  <div class="form-group">
    <label class="col-sm-3 control-label">Attachments</label>
    <div class="col-sm-9">
      <!-- Existing Attachments -->
      <div v-if="initialAttachments && initialAttachments.length > 0" class="margin-bottom-10">
         <p><strong>Existing Attachments:</strong></p>
         <ul class="list-unstyled">
           <li v-for="att in initialAttachments" :key="att.id">
             <div class="checkbox">
               <label>
                 <input type="checkbox" v-model="deletedAttachments" :value="att.id" class="attach-delete" />
                 Delete <a :href="att.url" target="_blank">{{ att.name }}</a>
               </label>
             </div>
           </li>
         </ul>
         <input type="hidden" name="fault-attachments_delete_ids" :value="deletedAttachments.join(',')" />
      </div>

      <!-- New Attachments -->
      <div>
         <p v-if="initialAttachments && initialAttachments.length > 0"><strong>Add New Attachments:</strong></p>
         <input type="file" name="fault-attachments" multiple @change="handleFileChange" class="form-control" style="height: auto;" />
         
         <table class="table table-condensed table-hover margin-top-10" v-if="selectedFiles.length > 0">
           <tbody id="attachment-names">
             <tr v-for="(file, idx) in selectedFiles" :key="idx">
               <td><i class="fa fa-paperclip fa-fw" aria-hidden="true"></i> {{ file.name }}</td>
             </tr>
           </tbody>
         </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  initialAttachments: {
    type: Array,
    default: () => []
  }
});

const deletedAttachments = ref([]);
const selectedFiles = ref([]);

const handleFileChange = (event) => {
  if (event.target.files) {
    selectedFiles.value = Array.from(event.target.files);
  } else {
    selectedFiles.value = [];
  }
};
</script>
