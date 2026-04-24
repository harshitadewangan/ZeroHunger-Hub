document.addEventListener("DOMContentLoaded", () => {
    // Flash message auto-dismiss
    const flashes = document.querySelectorAll(".flash");
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 300);
        }, 5000); // 5 seconds
    });

    // Notification Dropdown Toggle
    const notifBtn = document.getElementById("notif-btn");
    const notifDropdown = document.getElementById("notif-dropdown");
    if (notifBtn && notifDropdown) {
        notifBtn.addEventListener("click", (e) => {
            e.preventDefault();
            notifDropdown.classList.toggle("show");

            // Mark notifications as read
            const badge = document.getElementById("notif-badge");
            if (badge) {
                fetch('/notifications/read', { method: 'POST', credentials: 'same-origin' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        badge.style.display = 'none';
                    }
                });
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener("click", (e) => {
            if (!notifBtn.contains(e.target) && !notifDropdown.contains(e.target)) {
                notifDropdown.classList.remove("show");
            }
        });
    }

    const apiDeleteNotification = (id) => {
        return fetch(`/api/notifications/delete/${id}`, {
            method: 'DELETE',
            credentials: 'same-origin'
        }).then(r => r.json());
    };

    const apiClearNotifications = () => {
        return fetch('/api/notifications/clear', {
            method: 'POST',
            credentials: 'same-origin'
        }).then(r => r.json());
    };

    const updateNotifBadge = (count) => {
        const badge = document.getElementById('notif-badge');
        if (!badge) return;
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    };

    const showNoNotifications = () => {
        const placeholder = document.createElement('div');
        placeholder.className = 'notif-item';
        placeholder.style = 'padding: 15px; text-align: center; color: #94a3b8; font-size: 0.9rem;';
        placeholder.textContent = 'No new notifications.';
        const dropdown = document.getElementById('notif-dropdown');
        if (!dropdown) return;
        const existingItems = dropdown.querySelectorAll('.notif-item');
        existingItems.forEach(item => item.remove());
        dropdown.appendChild(placeholder);
    };

    document.addEventListener('click', function(e) {
        if (e.target.matches('.notif-delete-btn')) {
            const notifId = e.target.dataset.notifId;
            if (!notifId) return;
            apiDeleteNotification(notifId).then(data => {
                if (data.success) {
                    const notifElement = document.querySelector(`.notif-item[data-notif-id='${notifId}']`);
                    if (notifElement) notifElement.remove();
                    updateNotifBadge(data.unread_count);
                    if (!document.querySelector('.notif-item[data-notif-id]')) {
                        showNoNotifications();
                    }
                }
            });
        }
        if (e.target.matches('#clear-notifications-btn')) {
            e.preventDefault();
            apiClearNotifications().then(data => {
                if (data.success) {
                    updateNotifBadge(0);
                    showNoNotifications();
                }
            });
        }
    });

    const deleteButtons = document.querySelectorAll('.delete-post-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const foodId = button.dataset.foodId;
            if (!foodId) return;
            const confirmed = window.confirm('Are you sure you want to delete this post? This action cannot be undone.');
            if (!confirmed) return;
            fetch(`/api/delete_post/${foodId}`, {
                method: 'DELETE',
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const row = document.querySelector(`tr[data-food-id='${foodId}']`);
                    if (row) row.remove();
                    const tableBody = document.querySelector('table tbody');
                    if (tableBody && tableBody.querySelectorAll('tr').length === 0) {
                        const container = document.querySelector('.data-table-container');
                        if (container) {
                            container.innerHTML = `
                                <div class="glass-card" style="text-align: center; padding: 5rem 2rem;">
                                    <i class="fas fa-box-open" style="font-size: 4rem; color: #cbd5e1; margin-bottom: 2rem;"></i>
                                    <h2>No active listings.</h2>
                                    <p style="color: var(--text-muted);">You haven't posted any surplus food yet.</p>
                                    <a href="/add_food" class="btn-primary" style="margin-top: 2rem;">Create Your First Listing</a>
                                </div>
                            `;
                        }
                    }
                } else {
                    window.alert('Unable to delete the post. Please try again.');
                }
            })
            .catch(() => {
                window.alert('Unable to delete the post. Please try again.');
            });
        });
    });

    const forms = document.querySelectorAll("form");
    forms.forEach(form => {
        form.addEventListener("submit", (e) => {
            const btn = form.querySelector("button[type='submit']");
            if (btn) {
                setTimeout(() => {
                    btn.disabled = true;
                    btn.classList.add("loading");
                    btn.innerHTML = `<span class="spinner"></span> Processing...`;
                }, 10);
            }
        });
    });
});
