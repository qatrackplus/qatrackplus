<template>
  <div class="bulk-review-container">
    <div class="row">
      <div class="col-sm-12">
        <button id="submit-review"
                type="button"
                class="btn btn-primary btn-flat pull-right margin-r-5"
                title="Click to update the review status of the selected faults"
                @click="openModal"
        >
          <i class="fa fa-save"></i>
          Acknowledge Selected Faults
        </button>
      </div>
    </div>

    <!-- Teleport the modal to body so it displays properly over other elements -->
    <Teleport to="body">
      <div v-if="showModal" class="modal fade in" style="display: block; background: rgba(0,0,0,0.5);" tabindex="-1" role="dialog">
        <div class="modal-dialog" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <button type="button" class="close" @click="closeModal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
              <h4 class="modal-title">Confirm Bulk Review</h4>
            </div>
            <div class="modal-body">
              <div class="row">
                <div class="col-sm-12">
                  <p>You are about to update the review status for all the following faults:</p>
                  <form class="form">
                    <div class="form-group">
                      <table id="instance-summary" class="table table-bordered table-striped table-condensed fixed">
                        <thead>
                          <tr>
                            <th>Fault</th>
                            <th>Unit</th>
                            <th># of Faults</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(count, key) in summary" :key="key">
                            <td>{{ key.split('||')[0] }}</td>
                            <td>{{ key.split('||')[1] }}</td>
                            <td>{{ count }}</td>
                          </tr>
                          <tr v-if="Object.keys(summary).length === 0">
                            <td colspan="3" class="text-center">No faults selected.</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <p id="bulk-review-msg" v-html="message"></p>
                  </form>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-default" @click="closeModal">Cancel</button>
              <button id="confirm-update" type="button" class="btn btn-primary" @click="confirmUpdate" :disabled="isSubmitting || Object.keys(summary).length === 0">
                <span v-if="isSubmitting"><i class="fa fa-spinner fa-spin"></i> Confirming...</span>
                <span v-else>Confirm</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import axios from 'axios';

const showModal = ref(false);
const summary = ref({});
const selectedFaultIds = ref([]);
const message = ref('');
const isSubmitting = ref(false);

const openModal = () => {
  // Query the DOM for selected checkboxes in the listable table
  const checkboxes = document.querySelectorAll("#listable-table-fault_list_unreviewed tbody tr td input:checkbox:checked");
  
  // Find column indices
  const headers = Array.from(document.querySelectorAll("#listable-table-fault_list_unreviewed tr:first-child th")).map(el => el.innerText.toLowerCase());
  const siteIdx = headers.indexOf("site");
  const unitIdx = headers.indexOf("unit");
  const faultTypeIdx = headers.indexOf("fault type");
  
  const counter = {};
  const ids = [];
  
  checkboxes.forEach(el => {
    if (el.value === "") return;
    
    ids.push(el.dataset.fault);
    const row = el.closest("tr");
    const children = row.children;
    
    const site = siteIdx >= 0 ? (children[siteIdx].innerText || "Other") + ": " : "";
    const unit = site + (unitIdx >= 0 && children[unitIdx] ? children[unitIdx].innerText : "Unknown Unit");
    const ft = faultTypeIdx >= 0 && children[faultTypeIdx] ? children[faultTypeIdx].innerText : "Unknown Fault";
    const key = `${ft}||${unit}`;
    
    if (key in counter) {
      counter[key] += 1;
    } else {
      counter[key] = 1;
    }
  });
  
  // Sort the counter
  const sortedSummary = {};
  Object.keys(counter).sort((a, b) => counter[b] - counter[a]).forEach(k => {
    sortedSummary[k] = counter[k];
  });
  
  summary.value = sortedSummary;
  selectedFaultIds.value = ids;
  message.value = '';
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
};

const confirmUpdate = async () => {
  if (selectedFaultIds.value.length === 0) return;
  
  isSubmitting.value = true;
  message.value = '';
  
  try {
    const url = (window.QAURLs && window.QAURLs.FAULT_BULK_REVIEW) || '/faults/bulk_review/';
    
    // axios uses array format data: { faults: [1, 2] } -> defaults to faults[]=1&faults[]=2
    // We want traditional serialization `faults=1&faults=2` like jQuery did.
    // Use URLSearchParams
    const params = new URLSearchParams();
    selectedFaultIds.value.forEach(id => {
      params.append('faults', id);
    });
    
    // CSRF token is required since it's a POST to Django
    const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || 
                      document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
                      
    const res = await axios.post(url, params, {
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    
    if (res.data.ok) {
      location.reload();
    } else {
      message.value = '<span style="color: red"><em>Sorry reviewing the faults failed.</em></span>';
    }
  } catch (err) {
    console.error(err);
    message.value = '<span style="color: red"><em>Sorry reviewing the faults failed.</em></span>';
  } finally {
    isSubmitting.value = false;
  }
};

// Also attach the checkbox toggle all logic here
const handleSelectAll = (e) => {
  if (e.target.classList.contains("test-selected-toggle")) {
    const isChecked = e.target.checked;
    document.querySelectorAll("input.test-selected-toggle").forEach(el => {
      if (el !== e.target) el.checked = isChecked;
    });
    const table = e.target.closest("table");
    if (table) {
      table.querySelectorAll("input.test-selected").forEach(el => {
        el.checked = isChecked;
      });
    }
  }
};

onMounted(() => {
  // Hide select all if needed
  const firstToggle = document.querySelectorAll(".test-selected-toggle")[0];
  if (firstToggle) firstToggle.style.display = 'none';
  const firstBulkReview = document.querySelectorAll(".bulk-review-all")[0];
  if (firstBulkReview) firstBulkReview.style.display = 'none';
  
  document.addEventListener("change", handleSelectAll);
});

onBeforeUnmount(() => {
  document.removeEventListener("change", handleSelectAll);
});
</script>
