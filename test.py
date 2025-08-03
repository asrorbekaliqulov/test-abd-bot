import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches

# Dark mode
plt.style.use('dark_background')
sns.set_style("darkgrid")

# Ma'lumotlar (siz yuborgan JSONlardan olingan)
profile = {
    "name": "Asrorbek Aliqulov",
    "username": "asrorbekdev",
    "level": 5,
    "streak": 31,
    "badges": 8,
    "questions_attempted": 120,
    "correct_answers": 87,
    "wrong_answers": 33,
    "categories": {
        "Math": 35,
        "Science": 25,
        "History": 20,
        "Programming": 40
    },
    "weekly_activity": [2, 5, 4, 7, 6, 3, 4],  # Mon to Sun
}

fig = plt.figure(figsize=(14, 10))
gs = gridspec.GridSpec(3, 4, figure=fig)
fig.suptitle(f"{profile['name']} (@{profile['username']})", fontsize=20, color="white", fontweight="bold")

# 1. General Stats block
ax1 = fig.add_subplot(gs[0, :2])
ax1.axis('off')
box = patches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02", linewidth=1.5, edgecolor='deepskyblue', facecolor='#1e1e1e')
ax1.add_patch(box)
ax1.text(0.05, 0.75, f"Level: {profile['level']}", fontsize=14, color="deepskyblue")
ax1.text(0.05, 0.5, f"🔥 Streak: {profile['streak']} days", fontsize=14, color="orange")
ax1.text(0.05, 0.25, f"🏅 Badges: {profile['badges']}", fontsize=14, color="gold")

# 2. Pie chart - Correct vs Wrong
ax2 = fig.add_subplot(gs[0, 2:])
labels = ['Correct', 'Wrong']
sizes = [profile['correct_answers'], profile['wrong_answers']]
colors = ['#2ecc71', '#e74c3c']
ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
ax2.set_title("Answer Accuracy", color="white", fontsize=14)

# 3. Bar chart - Category performance
ax3 = fig.add_subplot(gs[1, :2])
categories = list(profile['categories'].keys())
values = list(profile['categories'].values())
sns.barplot(x=values, y=categories, palette="mako", ax=ax3)
ax3.set_title("Questions Solved per Category", color="white")
ax3.set_xlabel("Solved", color="white")
ax3.set_ylabel("Category", color="white")
ax3.tick_params(colors='white')

# 4. Line chart - Weekly activity
ax4 = fig.add_subplot(gs[1, 2:])
days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
sns.lineplot(x=days, y=profile['weekly_activity'], marker='o', color='lime', ax=ax4)
ax4.set_title("Weekly Activity", color="white")
ax4.set_xlabel("Day", color="white")
ax4.set_ylabel("Questions", color="white")
ax4.tick_params(colors='white')

# 5. Footer block
ax5 = fig.add_subplot(gs[2, :])
ax5.axis('off')
ax5.text(0.5, 0.5, "Created with ❤️ on TestAbd", fontsize=12, color='gray', ha='center')

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig("user_profile_stats.png")
plt.show()

