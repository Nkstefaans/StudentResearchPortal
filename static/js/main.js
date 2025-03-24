// Student Research Management System - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Toggle password visibility
    const togglePassword = document.querySelectorAll('.toggle-password');
    if (togglePassword) {
        togglePassword.forEach(button => {
            button.addEventListener('click', function() {
                const passwordField = document.querySelector(this.getAttribute('data-target'));
                const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
                passwordField.setAttribute('type', type);
                
                // Toggle icon
                this.querySelector('i').classList.toggle('fa-eye');
                this.querySelector('i').classList.toggle('fa-eye-slash');
            });
        });
    }
    
    // Handle dynamic form fields based on role selection
    const roleSelect = document.getElementById('role');
    if (roleSelect) {
        const studentFields = document.getElementById('student-fields');
        const lecturerFields = document.getElementById('lecturer-fields');
        const examinerFields = document.getElementById('examiner-fields');
        const postgradFields = document.getElementById('postgrad-fields');
        const commonFields = document.getElementById('common-fields');
        
        function toggleFields() {
            // Hide all role-specific fields
            if (studentFields) studentFields.classList.add('d-none');
            if (lecturerFields) lecturerFields.classList.add('d-none');
            if (examinerFields) examinerFields.classList.add('d-none');
            if (postgradFields) postgradFields.classList.add('d-none');
            
            // Show fields based on selected role
            const selectedRole = roleSelect.value;
            
            if (selectedRole === 'student' && studentFields) {
                studentFields.classList.remove('d-none');
                if (commonFields) commonFields.classList.remove('d-none');
            } else if (selectedRole === 'lecturer' && lecturerFields) {
                lecturerFields.classList.remove('d-none');
                if (commonFields) commonFields.classList.remove('d-none');
            } else if (selectedRole === 'examiner' && examinerFields) {
                examinerFields.classList.remove('d-none');
            } else if (selectedRole === 'postgrad_office' && postgradFields) {
                postgradFields.classList.remove('d-none');
            }
        }
        
        // Initial toggle
        toggleFields();
        
        // Toggle on change
        roleSelect.addEventListener('change', toggleFields);
    }
    
    // Custom file input display
    const fileInputs = document.querySelectorAll('input[type="file"]');
    if (fileInputs) {
        fileInputs.forEach(input => {
            input.addEventListener('change', function() {
                const fileNameDisplay = document.querySelector(`[data-file-display="${this.id}"]`);
                if (fileNameDisplay) {
                    if (this.files.length > 0) {
                        fileNameDisplay.textContent = this.files[0].name;
                    } else {
                        fileNameDisplay.textContent = 'No file chosen';
                    }
                }
            });
        });
    }
    
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (tooltips.length > 0) {
        tooltips.forEach(tooltip => {
            new bootstrap.Tooltip(tooltip);
        });
    }
    
    // Initialize popovers
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    if (popovers.length > 0) {
        popovers.forEach(popover => {
            new bootstrap.Popover(popover);
        });
    }
    
    // Deadline countdown
    const deadlineCounters = document.querySelectorAll('.deadline-counter');
    if (deadlineCounters) {
        deadlineCounters.forEach(counter => {
            const deadline = new Date(counter.getAttribute('data-deadline'));
            const now = new Date();
            const daysLeft = Math.ceil((deadline - now) / (1000 * 60 * 60 * 24));
            
            counter.textContent = daysLeft > 0 ? `${daysLeft} days left` : 'Overdue';
            
            if (daysLeft <= 7 && daysLeft > 0) {
                counter.classList.add('deadline-approaching');
            } else if (daysLeft <= 0) {
                counter.classList.add('deadline-overdue');
            }
        });
    }
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    if (forms) {
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                
                form.classList.add('was-validated');
            }, false);
        });
    }
    
    // Notification handling
    const notificationToggle = document.getElementById('notification-toggle');
    if (notificationToggle) {
        notificationToggle.addEventListener('click', function() {
            const notificationMenu = document.getElementById('notification-menu');
            if (notificationMenu) {
                notificationMenu.classList.toggle('show');
            }
        });
        
        // Close when clicking outside
        document.addEventListener('click', function(event) {
            const notificationMenu = document.getElementById('notification-menu');
            if (notificationMenu && notificationToggle) {
                if (!notificationMenu.contains(event.target) && !notificationToggle.contains(event.target)) {
                    notificationMenu.classList.remove('show');
                }
            }
        });
    }
    
    // Mark notification as read via AJAX
    const notificationReadButtons = document.querySelectorAll('.mark-notification-read');
    if (notificationReadButtons) {
        notificationReadButtons.forEach(button => {
            button.addEventListener('click', function(event) {
                event.preventDefault();
                const notificationId = this.getAttribute('data-notification-id');
                const notificationItem = document.getElementById(`notification-${notificationId}`);
                
                fetch(`/mark-notification-read/${notificationId}`)
                    .then(response => {
                        if (response.ok) {
                            if (notificationItem) {
                                notificationItem.classList.add('text-muted');
                                const badge = document.querySelector('.notification-badge');
                                if (badge) {
                                    let count = parseInt(badge.getAttribute('data-count')) - 1;
                                    if (count <= 0) {
                                        badge.removeAttribute('data-count');
                                    } else {
                                        badge.setAttribute('data-count', count);
                                    }
                                }
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Error marking notification as read:', error);
                    });
            });
        });
    }
    
    // Print report functionality
    const printReportButton = document.getElementById('print-report');
    if (printReportButton) {
        printReportButton.addEventListener('click', function() {
            window.print();
        });
    }
    
    // Institution uniqueness checking for examiner nominations
    const examinerSelects = document.querySelectorAll('[id^="examiner_"]');
    if (examinerSelects.length > 0) {
        const institutionWarning = document.getElementById('institution-warning');
        
        function checkInstitutions() {
            const selectedOptions = Array.from(examinerSelects)
                .map(select => select.options[select.selectedIndex])
                .filter(option => option.value !== '');
            
            const institutions = new Set();
            let hasDuplicates = false;
            
            selectedOptions.forEach(option => {
                const institution = option.getAttribute('data-institution');
                if (institution) {
                    if (institutions.has(institution.toLowerCase())) {
                        hasDuplicates = true;
                    } else {
                        institutions.add(institution.toLowerCase());
                    }
                }
            });
            
            if (institutionWarning) {
                if (hasDuplicates) {
                    institutionWarning.classList.remove('d-none');
                } else {
                    institutionWarning.classList.add('d-none');
                }
            }
        }
        
        examinerSelects.forEach(select => {
            select.addEventListener('change', checkInstitutions);
        });
        
        // Initial check
        checkInstitutions();
    }
});
