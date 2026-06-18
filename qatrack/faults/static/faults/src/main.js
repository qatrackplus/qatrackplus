import { createApp } from 'vue';

import FaultForm from './components/FaultForm.vue';
import UnreviewedFaultList from './components/UnreviewedFaultList.vue';

const mountedApps = new Map();

const initVueApps = () => {
  const mountApp = (id, Component) => {
    const el = document.getElementById(id);
    
    // If we previously mounted an app here, unmount it first to prevent leaks
    if (mountedApps.has(id)) {
      mountedApps.get(id).unmount();
      mountedApps.delete(id);
    }
    
    // If the target element exists in the new DOM, create and mount the new app
    if (el) {
      const app = createApp(Component);
      app.mount(el);
      mountedApps.set(id, app);
    }
  };

  mountApp('fault-form-app', FaultForm);
  mountApp('bulk-review-app', UnreviewedFaultList);
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', initVueApps);

// Initialize when HTMX swaps content
document.body.addEventListener('htmx:afterSettle', initVueApps);
