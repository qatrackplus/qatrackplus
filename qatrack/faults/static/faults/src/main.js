import { createApp } from 'vue';

import FaultForm from './components/FaultForm.vue';
import UnreviewedFaultList from './components/UnreviewedFaultList.vue';
// import FaultReviewButton from './components/FaultReviewButton.vue';

const initVueApps = () => {
  const faultFormEl = document.getElementById('fault-form-app');
  if (faultFormEl) {
    const app = createApp(FaultForm);
    app.mount(faultFormEl);
  }

  const bulkReviewEl = document.getElementById('bulk-review-app');
  if (bulkReviewEl) {
    const app = createApp(UnreviewedFaultList);
    app.mount(bulkReviewEl);
  }

  const faultReviewEl = document.getElementById('fault-review-app');
  if (faultReviewEl) {
    // const app = createApp(FaultReviewButton);
    // app.mount(faultReviewEl);
  }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', initVueApps);

// Initialize when HTMX swaps content
document.body.addEventListener('htmx:afterSettle', initVueApps);
