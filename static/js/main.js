document.addEventListener('DOMContentLoaded', function() {
    // Fix for dropdown display in modals
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Find the dropdown menu associated with this toggle
            const menu = this.nextElementSibling;
            
            // Close all other open dropdowns
            document.querySelectorAll('.dropdown-menu.show').forEach(openMenu => {
                if (openMenu !== menu) {
                    openMenu.classList.remove('show');
                }
            });
            
            // Toggle this dropdown
            menu.classList.toggle('show');
        });
    });
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });
    
    // Handle selection in custom dropdowns
    document.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const dropdown = this.closest('.dropdown');
            const toggle = dropdown.querySelector('.dropdown-toggle');
            const hiddenInput = dropdown.querySelector('input[type="hidden"]');
            
            // Update the toggle button text
            toggle.textContent = this.textContent.trim();
            
            // Update the hidden input value
            if (hiddenInput) {
                hiddenInput.value = this.getAttribute('data-value');
            }
            
            // Close the dropdown
            this.closest('.dropdown-menu').classList.remove('show');
        });
    });
}); 