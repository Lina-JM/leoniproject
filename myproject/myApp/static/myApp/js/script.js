document.addEventListener("DOMContentLoaded", function() {
    // Initialize based on which form exists on the page
    if (document.getElementById('compare-form')) {
        setupMainForm();
    } else if (document.getElementById('update-form')) {
        setupUpdateForm();
    }

    // Auto-close alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000);
    });
});

// ==================== MAIN FORM SETUP ====================
function setupMainForm() {
    const form = document.getElementById("compare-form");
    const errorDiv = document.getElementById("error-message");
    const file1Input = document.getElementById("id_file1");
    const file2Input = document.getElementById("id_file2");
    const date1Input = document.getElementById("id_date1");
    const date2Input = document.getElementById("id_date2");

    // Auto-fill dates from filenames
    file1Input?.addEventListener('change', () => autoFillDateFromFilename(file1Input, date1Input));
    file2Input?.addEventListener('change', () => autoFillDateFromFilename(file2Input, date2Input));

    // Form validation
    form?.addEventListener('submit', function(e) {
        clearError(errorDiv);

        try {
            validateRequiredFields([file1Input, file2Input, date1Input, date2Input]);
            
            const date1 = parseWeekString(date1Input.value);
            const date2 = parseWeekString(date2Input.value);
            validateWeekOrder(date1, date2);

        } catch (err) {
            // Add appropriate error class based on error type
            if (err.message.includes("Header mismatch")) {
                errorDiv.classList.add('header-error');
            } else if (err.message.includes("KW(X) must be later")) {
                errorDiv.classList.add('date-error');
            }
            handleFormError(e, errorDiv, err);
        }
    });
}

// ==================== UPDATE FORM SETUP ====================
function setupUpdateForm() {
    const form = document.getElementById("update-form");
    const errorDiv = document.getElementById("error-message");
    const date1Input = document.getElementById("date1");
    const date2Input = document.getElementById("date2");
    const file1Input = document.getElementById("file1");
    const file2Input = document.getElementById("file2");

    // Auto-fill dates from filenames
    file1Input?.addEventListener('change', function() {
        autoFillDateFromFilename(file1Input, date1Input);
    });
    
    file2Input?.addEventListener('change', function() {
        autoFillDateFromFilename(file2Input, date2Input);
    });

    // Form validation
    form?.addEventListener('submit', function(e) {
        clearError(errorDiv);

        try {
            // Only validate if dates are provided (they're optional)
            if (date1Input.value || date2Input.value) {
                if (!date1Input.value || !date2Input.value) {
                    throw new Error("Please provide both week inputs or leave both empty");
                }

                const date1 = parseWeekString(date1Input.value);
                const date2 = parseWeekString(date2Input.value);
                validateWeekOrder(date1, date2);
            }
        } catch (err) {
            // Add appropriate error class based on error type
            if (err.message.includes("Header mismatch")) {
                errorDiv.classList.add('header-error');
            } else if (err.message.includes("KW(X) must be later")) {
                errorDiv.classList.add('date-error');
            } else if (err.message.includes("Please provide both week inputs")) {
                errorDiv.classList.add('date-error');
            }
            handleFormError(e, errorDiv, err);
        }
    });
}

// ==================== SHARED UTILITY FUNCTIONS ====================
function autoFillDateFromFilename(fileInput, dateInput) {
    const file = fileInput.files[0];
    if (file) {
        const match = file.name.match(/KW[\s_-]?(\d{1,2})/i);
        if (match) {
            const week = parseInt(match[1]);
            const year = new Date().getFullYear();
            dateInput.value = `${year}-W${week.toString().padStart(2, '0')}`;
        }
    }
}

function parseWeekString(weekStr) {
    const [year, week] = weekStr.split('-W').map(Number);
    if (isNaN(year) || isNaN(week) || week < 1 || week > 53) {
        throw new Error("Invalid date format. Use YYYY-Www (e.g., 2025-W21)");
    }
    const date = new Date(year, 0, 1 + (week - 1) * 7);
    while (date.getDay() !== 1) {
        date.setDate(date.getDate() - 1);
    }
    return date;
}

function validateWeekOrder(date1, date2) {
    if (date1 <= date2) {
        throw new Error("KW(X) must be after KW(X-N)");
    }
}

function validateRequiredFields(fields) {
    const missingFields = fields.filter(field => {
        if (field.type === 'file') return !field.files[0];
        return !field.value.trim();
    });
    
    if (missingFields.length > 0) {
        throw new Error("All fields are required");
    }
}

function clearError(errorDiv) {
    if (errorDiv) {
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
        errorDiv.classList.remove('header-error', 'date-error');
    }
}

function handleFormError(event, errorDiv, error) {
    event.preventDefault();
    if (errorDiv) {
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
        errorDiv.scrollIntoView({ behavior: 'smooth' });
        
        // Add appropriate error class
        if (error.message.includes("Header mismatch")) {
            errorDiv.classList.add('header-error');
        } else if (error.message.includes("KW(X) must be later")) {
            errorDiv.classList.add('date-error');
        } else if (error.message.includes("must be an Excel file")) {
            errorDiv.classList.add('validation-error');
        }
    }
}