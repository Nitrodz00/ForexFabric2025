// الحصول على معرف المستخدم من URL
let userId = new URLSearchParams(window.location.search).get('user_id');
let startTime = Date.now();
let countdownInterval;
let userData = null;

// بدء التطبيق عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEventListeners();
});

// تهيئة التطبيق
async function initApp() {
    if (!userId) {
        showToast('خطأ', 'معرف المستخدم غير موجود في الرابط', 'error');
        return;
    }

    try {
        await fetchUserData();
        await fetchLeaderboard();
        await fetchActivityHistory();
    } catch (error) {
        console.error('خطأ في تهيئة التطبيق:', error);
        showToast('خطأ', 'حدث خطأ أثناء تحميل البيانات', 'error');
    }
}

// جلب بيانات المستخدم من الخادم
async function fetchUserData() {
    try {
        const response = await fetch(`/api/user/${userId}`);
        
        if (!response.ok) {
            throw new Error(`خطأ في الاستجابة: ${response.status}`);
        }
        
        userData = await response.json();
        updateUI();
    } catch (error) {
        console.error('خطأ في جلب بيانات المستخدم:', error);
        throw error;
    }
}

// تحديث واجهة المستخدم بالبيانات
function updateUI() {
    if (!userData) return;
    
    // تحديث معلومات المستخدم
    document.getElementById('current-points').textContent = userData.points;
    document.getElementById('total-points').textContent = userData.total_points;
    document.getElementById('referrals-count').textContent = userData.referrals_count;
    
    // تحديث زر المطالبة اليومية
    updateClaimButton();
    
    // تحديث حالة المواقع الاجتماعية
    updateSocialMediaButtons();
}

// تحديث زر المطالبة اليومية
function updateClaimButton() {
    const claimBtn = document.getElementById('daily-claim-btn');
    
    if (userData.can_claim) {
        claimBtn.disabled = false;
        claimBtn.textContent = 'المطالبة اليومية';
        document.getElementById('next-claim-time').textContent = 'متاح الآن';
    } else {
        claimBtn.disabled = true;
        claimBtn.textContent = 'تم المطالبة اليوم';
        
        if (userData.next_claim_time > 0) {
            startCountdown(userData.next_claim_time);
        }
    }
}

// تحديث أزرار مواقع التواصل الاجتماعي
function updateSocialMediaButtons() {
    // إنشاء لوحة المواقع الاجتماعية إذا لم تكن موجودة
    if (!document.getElementById('social-media-container')) {
        createSocialMediaUI();
    }
    
    // تحديث حالة الأزرار بناءً على المواقع التي تمت زيارتها
    if (userData.visited_socials && userData.social_links) {
        for (const socialType in userData.social_links) {
            const button = document.getElementById(`social-${socialType}-btn`);
            if (button) {
                if (userData.visited_socials.includes(socialType)) {
                    button.classList.add('visited');
                    button.querySelector('.visit-status').textContent = '✓ تمت الزيارة';
                    button.disabled = true;
                } else {
                    button.classList.remove('visited');
                    button.querySelector('.visit-status').textContent = '+50 نقطة';
                    button.disabled = false;
                }
            }
        }
    }
}

// إنشاء واجهة مواقع التواصل الاجتماعي
function createSocialMediaUI() {
    if (!userData.social_links) return;
    
    // إنشاء حاوية مواقع التواصل الاجتماعي
    const container = document.createElement('div');
    container.id = 'social-media-container';
    container.innerHTML = '<h2>زيارة مواقع التواصل الاجتماعي</h2>';
    
    // إضافة الأزرار
    const buttonsContainer = document.createElement('div');
    buttonsContainer.className = 'social-media-buttons';
    buttonsContainer.style.display = 'grid';
    buttonsContainer.style.gridTemplateColumns = 'repeat(auto-fill, minmax(220px, 1fr))';
    buttonsContainer.style.gap = '1rem';
    buttonsContainer.style.marginTop = '1rem';
    
    const socialIcons = {
        instagram: '📸',
        telegram: '📱',
        website: '🌐',
        support: '🆘'
    };
    
    const socialNames = {
        instagram: 'انستغرام',
        telegram: 'تيليغرام',
        website: 'الموقع الرسمي',
        support: 'الدعم الفني'
    };
    
    for (const socialType in userData.social_links) {
        const button = document.createElement('div');
        button.id = `social-${socialType}-btn`;
        button.className = 'social-button';
        button.style.backgroundColor = 'var(--zinc-800)';
        button.style.borderRadius = '0.5rem';
        button.style.padding = '1rem';
        button.style.display = 'flex';
        button.style.flexDirection = 'column';
        button.style.alignItems = 'center';
        button.style.gap = '0.5rem';
        button.style.cursor = 'pointer';
        button.style.transition = 'all 0.3s ease';
        button.style.border = '1px solid var(--amber-500)';
        
        button.innerHTML = `
            <div class="social-icon" style="font-size: 2rem;">${socialIcons[socialType] || '🔗'}</div>
            <div class="social-name" style="font-weight: bold; color: var(--amber-400);">${socialNames[socialType] || socialType}</div>
            <div class="visit-status" style="font-size: 0.875rem; color: var(--amber-500);">+50 نقطة</div>
        `;
        
        button.addEventListener('click', () => visitSocialMedia(socialType, userData.social_links[socialType]));
        
        buttonsContainer.appendChild(button);
    }
    
    container.appendChild(buttonsContainer);
    
    // إضافة الحاوية بعد معلومات المستخدم وقبل سجل النشاطات
    const activityContainer = document.getElementById('activities-container');
    if (activityContainer) {
        activityContainer.parentNode.insertBefore(container, activityContainer);
    } else {
        document.getElementById('user-data-container').appendChild(container);
    }
}

// زيارة موقع تواصل اجتماعي وتسجيل النشاط
async function visitSocialMedia(socialType, url) {
    // فتح الموقع في نافذة جديدة
    window.open(url, '_blank');
    
    try {
        // تسجيل الزيارة في الخادم
        const response = await fetch(`/api/social_visit/${userId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ social_type: socialType })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // تحديث بيانات المستخدم
            userData.points = data.points;
            userData.total_points = data.total_points;
            if (!userData.visited_socials) userData.visited_socials = [];
            userData.visited_socials.push(socialType);
            
            // تحديث واجهة المستخدم
            updateUI();
            
            // إظهار رسالة النجاح
            showToast('تم بنجاح', data.message, 'success');
            
            // تحديث سجل النشاطات
            fetchActivityHistory();
        } else {
            showToast('تنبيه', data.message, 'warning');
        }
    } catch (error) {
        console.error('خطأ في تسجيل زيارة الموقع:', error);
        showToast('خطأ', 'حدث خطأ أثناء تسجيل الزيارة', 'error');
    }
}

// بدء العد التنازلي للمطالبة التالية
function startCountdown(seconds) {
    // إيقاف أي عداد سابق
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    updateCountdownDisplay(seconds);
    
    countdownInterval = setInterval(() => {
        seconds--;
        
        if (seconds <= 0) {
            clearInterval(countdownInterval);
            userData.can_claim = true;
            updateClaimButton();
        } else {
            updateCountdownDisplay(seconds);
        }
    }, 1000);
}

// تحديث عرض العد التنازلي
function updateCountdownDisplay(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    
    const timeDisplay = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    document.getElementById('next-claim-time').textContent = timeDisplay;
}

// جلب وعرض تاريخ النشاطات
async function fetchActivityHistory() {
    try {
        const response = await fetch(`/api/activities/${userId}?limit=10`);
        if (!response.ok) {
            throw new Error(`خطأ في الاستجابة: ${response.status}`);
        }
        
        const data = await response.json();
        updateActivityHistory(data.activities);
    } catch (error) {
        console.error('خطأ في جلب تاريخ النشاطات:', error);
    }
}

// تحديث عرض سجل النشاطات
function updateActivityHistory(activities) {
    const activityList = document.getElementById('activities-list');
    activityList.innerHTML = '';
    
    const activityIcons = {
        daily_claim: '🎁',
        referral: '👥',
        task_completion: '✅',
        social_instagram: '📸',
        social_telegram: '📱',
        social_website: '🌐',
        social_support: '🆘',
        withdrawal: '💸'
    };
    
    const activityNames = {
        daily_claim: 'المكافأة اليومية',
        referral: 'إحالة صديق',
        task_completion: 'إكمال مهمة',
        social_instagram: 'زيارة انستغرام',
        social_telegram: 'زيارة تيليغرام',
        social_website: 'زيارة الموقع الرسمي',
        social_support: 'زيارة الدعم الفني',
        withdrawal: 'سحب النقاط'
    };
    
    if (activities && activities.length > 0) {
        activities.forEach(activity => {
            const date = new Date(activity.created_at);
            const formattedDate = `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
            
            const activityType = activity.activity_type;
            const icon = activityIcons[activityType] || '🔹';
            const name = activityNames[activityType] || activityType;
            
            const activityItem = document.createElement('div');
            activityItem.className = 'activity-item';
            activityItem.innerHTML = `
                <div class="activity-icon" style="display: inline-block; margin-left: 8px;">${icon}</div>
                <div class="activity-details" style="display: inline-block;">
                    <div class="activity-name">${name}</div>
                    <div class="activity-date">${formattedDate}</div>
                </div>
                <div class="activity-points" style="float: left;">
                    ${activity.points > 0 ? '+' : ''}${activity.points} نقطة
                </div>
            `;
            
            activityList.appendChild(activityItem);
        });
    } else {
        activityList.innerHTML = '<div class="no-activities">لا توجد أنشطة حتى الآن</div>';
    }
}

// جلب وعرض لوحة المتصدرين
async function fetchLeaderboard() {
    try {
        const response = await fetch('/api/leaderboard?limit=10');
        if (!response.ok) {
            throw new Error(`خطأ في الاستجابة: ${response.status}`);
        }
        
        const data = await response.json();
        updateLeaderboard(data.leaderboard);
    } catch (error) {
        console.error('خطأ في جلب لوحة المتصدرين:', error);
    }
}

// تحديث عرض لوحة المتصدرين
function updateLeaderboard(leaderboard) {
    const leaderboardContainer = document.getElementById('leaderboard-container');
    
    // إنشاء لوحة المتصدرين إذا لم تكن موجودة
    if (!leaderboardContainer) {
        const container = document.createElement('div');
        container.id = 'leaderboard-container';
        container.style.display = 'none';
        container.innerHTML = `
            <h2>لوحة المتصدرين</h2>
            <div id="leaderboard-list" style="margin-top: 1rem;"></div>
            <button id="close-leaderboard-btn" class="action-button" style="margin-top: 1rem;">إغلاق</button>
        `;
        
        document.body.appendChild(container);
        
        document.getElementById('close-leaderboard-btn').addEventListener('click', () => {
            document.getElementById('leaderboard-container').style.display = 'none';
        });
    }
    
    const leaderboardList = document.getElementById('leaderboard-list');
    leaderboardList.innerHTML = '';
    
    if (leaderboard && leaderboard.length > 0) {
        // إنشاء جدول المتصدرين
        const table = document.createElement('table');
        table.className = 'leaderboard-table';
        table.style.width = '100%';
        table.style.borderCollapse = 'collapse';
        
        // إنشاء رأس الجدول
        const thead = document.createElement('thead');
        thead.innerHTML = `
            <tr style="border-bottom: 1px solid var(--zinc-700);">
                <th style="padding: 0.5rem; text-align: center;">المركز</th>
                <th style="padding: 0.5rem; text-align: right;">المستخدم</th>
                <th style="padding: 0.5rem; text-align: left;">النقاط</th>
            </tr>
        `;
        table.appendChild(thead);
        
        // إنشاء جسم الجدول
        const tbody = document.createElement('tbody');
        leaderboard.forEach((entry, index) => {
            const isCurrentUser = entry.user_id.toString() === userId;
            const row = document.createElement('tr');
            
            if (isCurrentUser) {
                row.style.backgroundColor = 'rgba(251, 191, 36, 0.2)';
                row.style.fontWeight = 'bold';
            }
            
            row.style.borderBottom = '1px solid var(--zinc-700)';
            
            const rankEmoji = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}`;
            
            row.innerHTML = `
                <td style="padding: 0.5rem; text-align: center;">${rankEmoji}</td>
                <td style="padding: 0.5rem; text-align: right;">${entry.username}</td>
                <td style="padding: 0.5rem; text-align: left; color: var(--amber-400);">${entry.points}</td>
            `;
            
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        leaderboardList.appendChild(table);
    } else {
        leaderboardList.innerHTML = '<div style="text-align: center; padding: 1rem;">لا توجد بيانات متاحة</div>';
    }
}

// إعداد أحداث وأزرار واجهة المستخدم
function setupEventListeners() {
    // زر المطالبة اليومية
    document.getElementById('daily-claim-btn').addEventListener('click', async () => {
        try {
            const response = await fetch(`/api/daily_claim/${userId}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                userData.points = data.points;
                userData.total_points = data.total_points;
                userData.can_claim = false;
                userData.next_claim_time = 24 * 60 * 60; // 24 ساعة بالثواني
                
                updateUI();
                showToast('تم بنجاح', data.message, 'success');
                
                // تحديث سجل النشاطات
                fetchActivityHistory();
            } else {
                if (data.seconds_remaining) {
                    showToast('تنبيه', 'لا يمكنك المطالبة الآن، يرجى الانتظار', 'warning');
                    startCountdown(data.seconds_remaining);
                } else {
                    showToast('تنبيه', data.message, 'warning');
                }
            }
        } catch (error) {
            console.error('خطأ في المطالبة اليومية:', error);
            showToast('خطأ', 'حدث خطأ أثناء المطالبة اليومية', 'error');
        }
    });
    
    // زر المهام المتاحة (سيتم تنفيذه لاحقًا)
    document.getElementById('tasks-btn').addEventListener('click', () => {
        showToast('قريبًا', 'سيتم إضافة المهام قريبًا', 'info');
    });
    
    // زر الإحالة
    document.getElementById('referral-btn').addEventListener('click', () => {
        const referralLink = `https://t.me/ForexFabricPointsBot?start=${userId}`;
        
        // إنشاء النافذة المنبثقة للإحالة
        const referralContainer = document.createElement('div');
        referralContainer.className = 'referral-modal';
        referralContainer.style.position = 'fixed';
        referralContainer.style.top = '50%';
        referralContainer.style.left = '50%';
        referralContainer.style.transform = 'translate(-50%, -50%)';
        referralContainer.style.backgroundColor = 'var(--zinc-800)';
        referralContainer.style.padding = '2rem';
        referralContainer.style.borderRadius = '0.75rem';
        referralContainer.style.border = '2px solid var(--amber-400)';
        referralContainer.style.zIndex = '1000';
        referralContainer.style.maxWidth = '90%';
        referralContainer.style.width = '400px';
        referralContainer.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.5)';
        
        referralContainer.innerHTML = `
            <h2 style="color: var(--amber-400); margin-top: 0;">دعوة صديق</h2>
            <p>انسخ الرابط التالي وأرسله لأصدقائك. عندما يقومون بتسجيل الدخول، ستحصل على 50 نقطة مكافأة!</p>
            <div class="referral-link-container" style="display: flex; margin: 1rem 0;">
                <input type="text" id="referral-link-input" value="${referralLink}" 
                       style="flex: 1; padding: 0.75rem; border-radius: 0.5rem 0 0 0.5rem; background-color: var(--zinc-900); color: white; border: 1px solid var(--amber-500); border-right: none;" readonly>
                <button id="copy-referral-btn" 
                        style="background-color: var(--amber-500); color: var(--zinc-900); border: none; border-radius: 0 0.5rem 0.5rem 0; padding: 0 1rem; cursor: pointer;">نسخ</button>
            </div>
            <button id="close-referral-btn" 
                    style="background-color: var(--zinc-700); color: white; border: none; border-radius: 0.5rem; padding: 0.75rem 1.5rem; width: 100%; margin-top: 1rem; cursor: pointer;">إغلاق</button>
        `;
        
        // إضافة طبقة خلفية معتمة
        const overlay = document.createElement('div');
        overlay.className = 'overlay';
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        overlay.style.zIndex = '999';
        
        document.body.appendChild(overlay);
        document.body.appendChild(referralContainer);
        
        // إضافة وظائف للأزرار
        document.getElementById('copy-referral-btn').addEventListener('click', () => {
            const linkInput = document.getElementById('referral-link-input');
            linkInput.select();
            document.execCommand('copy');
            showToast('تم النسخ', 'تم نسخ رابط الإحالة بنجاح', 'success');
        });
        
        document.getElementById('close-referral-btn').addEventListener('click', () => {
            document.body.removeChild(overlay);
            document.body.removeChild(referralContainer);
        });
    });
    
    // زر لوحة المتصدرين
    document.getElementById('leaderboard-btn').addEventListener('click', () => {
        const leaderboardContainer = document.getElementById('leaderboard-container');
        if (leaderboardContainer) {
            leaderboardContainer.style.display = 'block';
            
            // إضافة طبقة خلفية معتمة
            const overlay = document.createElement('div');
            overlay.className = 'overlay';
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
            overlay.style.zIndex = '999';
            
            // إعادة تصميم لوحة المتصدرين
            leaderboardContainer.style.position = 'fixed';
            leaderboardContainer.style.top = '50%';
            leaderboardContainer.style.left = '50%';
            leaderboardContainer.style.transform = 'translate(-50%, -50%)';
            leaderboardContainer.style.backgroundColor = 'var(--zinc-800)';
            leaderboardContainer.style.padding = '2rem';
            leaderboardContainer.style.borderRadius = '0.75rem';
            leaderboardContainer.style.border = '2px solid var(--amber-400)';
            leaderboardContainer.style.zIndex = '1000';
            leaderboardContainer.style.maxWidth = '90%';
            leaderboardContainer.style.width = '500px';
            leaderboardContainer.style.maxHeight = '80vh';
            leaderboardContainer.style.overflowY = 'auto';
            leaderboardContainer.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.5)';
            
            document.body.appendChild(overlay);
            
            // تحديث مكان إغلاق اللوحة
            document.getElementById('close-leaderboard-btn').addEventListener('click', () => {
                document.body.removeChild(overlay);
                leaderboardContainer.style.display = 'none';
            });
            
            // إغلاق اللوحة عند النقر على الخلفية
            overlay.addEventListener('click', () => {
                document.body.removeChild(overlay);
                leaderboardContainer.style.display = 'none';
            });
            
            // منع إغلاق اللوحة عند النقر عليها
            leaderboardContainer.addEventListener('click', (event) => {
                event.stopPropagation();
            });
        }
    });
}

// عرض إشعار منبثق
function showToast(title, message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toast-title');
    const toastDescription = document.getElementById('toast-description');
    
    // تعيين النص
    toastTitle.textContent = title;
    toastDescription.textContent = message;
    
    // تعيين لون الإشعار حسب النوع
    const typeColors = {
        success: 'var(--green-400)',
        error: 'var(--red-400)',
        warning: 'var(--yellow-400)',
        info: 'var(--blue-400)'
    };
    
    toast.style.borderLeftColor = typeColors[type] || typeColors.info;
    toastTitle.style.color = typeColors[type] || typeColors.info;
    
    // عرض الإشعار
    toast.classList.add('show');
    
    // إخفاء الإشعار بعد 3 ثوانٍ
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}