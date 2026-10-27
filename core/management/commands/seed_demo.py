from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (Achievement, Assignment, Course, Enrollment, Goal, Grade, Group, Message,
                           PracticeActivity, PracticeSession, Profile, Task, TutorNote, UserAchievement,
                           WeeklyProgress)
from core.stats import monday_of

COURSES = [
    # slug, title, subtitle, icon, color, featured, club, description
    ("english", "English", "Reading • Writing • Speaking • Listening", "book-open", "teal", True, False,
     "Develop all four English skills with practice, mock exams and feedback."),
    ("digital-skills", "Digital Skills", "Technology • Online Tools • Productivity", "laptop", "blue", True, False,
     "Learn to work confidently with technology, online tools and productivity apps."),
    ("critical-thinking", "Critical Thinking", "Analysis • Problem Solving • Creativity", "bulb", "purple", True, False,
     "Analyse information, solve problems and think independently."),
    ("english-mocks", "English Mock Exams", "Full Listening • Full Reading • Full Writing", "certificate", "orange", False, False,
     "Extra lessons: full listening mock, full reading mock and full writing mock."),
    ("mathematics-club", "Mathematics Club", "Explore • Learn • Solve • Succeed", "star", "green", False, True,
     "Improve problem-solving skills, enjoy math games and puzzles, and prepare for competitions."),
    ("it-club", "IT Club", "Programming • Web Design • Graphic Design", "laptop", "blue", False, True,
     "Learn about technology and develop digital skills: programming, web design, graphic design."),
    ("uzbekistan-history-club", "Uzbekistan History Club", "Figures • Ancient Cities • Traditions", "trophy", "orange", False, True,
     "Knowing our history means knowing our roots! Famous figures, ancient cities and national traditions."),
    ("mother-tongue-club", "Mother Tongue Club", "Learn • Read • Speak • Create", "pencil", "purple", False, True,
     "Improve your Uzbek: grammar, spelling, literature and new words through games and activities."),
]

ACTIVITIES = [
    ("speaking", "Speaking Practice – Part 1", "english", 15, "Introduce yourself and answer everyday questions."),
    ("speaking", "Speaking Practice – Part 2", "english", 20, "Talk for two minutes about a topic card."),
    ("listening", "Listening Practice – Conversations", "english", 20, "Listen to short dialogues and answer questions."),
    ("listening", "Full Listening Mock", "english-mocks", 40, "Complete listening mock exam."),
    ("writing", "Writing Workshop – Email", "english", 30, "Write a formal and an informal email."),
    ("writing", "Full Writing Mock", "english-mocks", 60, "Complete writing mock exam."),
    ("quizzes", "Quiz: Communication", "critical-thinking", 20, "Test your communication skills."),
    ("quizzes", "Math Challenge", "mathematics-club", 25, "Solve puzzles and logic problems."),
    ("quizzes", "Full Reading Mock", "english-mocks", 60, "Complete reading mock exam."),
]

ACHIEVEMENTS = [
    ("First Steps", "Complete your first practice session.", 20, "star", "orange", False),
    ("Streak Master", "Practise 7 days in a row.", 100, "trophy", "orange", False),
    ("English Starter Certificate", "Finish the English starter level.", 150, "certificate", "teal", True),
    ("Digital Skills Certificate", "Finish Digital Skills.", 150, "certificate", "blue", True),
    ("Critical Thinking Certificate", "Finish Critical Thinking.", 150, "certificate", "purple", True),
    ("Math Club Certificate", "Complete Mathematics Club.", 150, "certificate", "green", True),
    ("IT Club Certificate", "Complete IT Club.", 150, "certificate", "blue", True),
]

# username, first, last, points, days since last login, english progress
DEMO_STUDENTS = [
    ("aziza", "Aziza", "Karimova", 980, 1, 64),
    ("bobur", "Bobur", "Rahimov", 1120, 10, 48),
    ("dilnoza", "Dilnoza", "Yusupova", 1410, 2, 91),
    ("sardor", "Sardor", "Nazarov", 760, 15, 30),
    ("madina", "Madina", "Abdullayeva", 1330, 3, 77),
]


def make_user(username, first, last, password="pearson123", role="student"):
    user, created = User.objects.get_or_create(username=username, defaults=dict(
        first_name=first, last_name=last, email=f"{username}@pearson.uz"))
    if created:
        user.set_password(password)
        user.save()
    Profile.objects.filter(user=user).update(role=role)
    return user


class Command(BaseCommand):
    help = "Demo ma'lumotlar: o'quvchi jasmeen / tutor tutor1 (parol: pearson123)"

    def handle(self, *args, **opts):
        today = timezone.localdate()
        now = timezone.now()

        courses = {}
        for i, (slug, title, sub, icon, color, feat, club, desc) in enumerate(COURSES):
            courses[slug], _ = Course.objects.update_or_create(slug=slug, defaults=dict(
                title=title, subtitle=sub, icon=icon, color=color, featured=feat, is_club=club,
                description=desc, order=i))

        for kind, title, cslug, minutes, desc in ACTIVITIES:
            PracticeActivity.objects.get_or_create(title=title, defaults=dict(
                kind=kind, course=courses[cslug], minutes=minutes, description=desc))

        ach = {}
        for title, desc, pts, icon, color, cert in ACHIEVEMENTS:
            ach[title], _ = Achievement.objects.get_or_create(title=title, defaults=dict(
                description=desc, points=pts, icon=icon, color=color, is_certificate=cert))

        # ---------- Asosiy demo o'quvchi ----------
        user = make_user("jasmeen", "Jasmeen", "Sunnatullayeva")
        user.email = "jasmeen@pearson.uz"
        user.last_login = now
        user.save()
        Profile.objects.filter(user=user).update(points=1250, level=3, level_points=750, level_target=1500,
                                                 practice_goal=20)

        for slug, prog, mile in [("english", 78, 4), ("digital-skills", 62, 3), ("critical-thinking", 55, 3),
                                 ("mathematics-club", 100, 1), ("it-club", 100, 1),
                                 ("uzbekistan-history-club", 100, 1)]:
            Enrollment.objects.update_or_create(user=user, course=courses[slug],
                                                defaults=dict(progress=prog, milestone=mile))

        if not user.tasks.filter(assignment__isnull=True).exists():
            for title, slug, kind, mins, delta in [
                ("Speaking Practice – Part 1", "english", "speaking", 15, 0),
                ("Writing Workshop", "english", "writing", 30, 1),
                ("Digital Skills Module 2", "digital-skills", "digital", 45, 2),
                ("Quiz: Communication", "critical-thinking", "quiz", 20, 3),
            ]:
                Task.objects.create(user=user, title=title, course=courses[slug], kind=kind,
                                    minutes=mins, due_date=today + timedelta(days=delta))

        monday = monday_of(today)
        for wd, pct in enumerate([60, 75, 68, 82, 70, 90, 76]):
            WeeklyProgress.objects.update_or_create(user=user, week=monday, weekday=wd, defaults=dict(percent=pct))

        if not user.practice_sessions.exists():
            acts = list(PracticeActivity.objects.all())
            for i in range(12):
                PracticeSession.objects.create(user=user, activity=acts[i % len(acts)],
                                               created=now - timedelta(days=i // 2))

        if not user.grades.filter(task__isnull=True).exists():
            for slug, title, score, back in [("english", "Reading test – Unit 3", 88, 2),
                                             ("english", "Speaking assessment", 92, 6),
                                             ("digital-skills", "Module 1 test", 81, 9),
                                             ("critical-thinking", "Logic quiz", 74, 12),
                                             ("mathematics-club", "Olympiad prep test", 95, 15)]:
                Grade.objects.create(user=user, course=courses[slug], title=title, score=score,
                                     date=today - timedelta(days=back))

        UserAchievement.objects.get_or_create(user=user, achievement=ach["First Steps"])
        UserAchievement.objects.get_or_create(user=user, achievement=ach["English Starter Certificate"])

        if not user.inbox.filter(author__isnull=True).exists():
            Message.objects.create(recipient=user, sender="Pearson Team", subject="Welcome to Pearson Technikum UZ!",
                                   body="Learn today, lead tomorrow! Here you can see your grades, homework, "
                                        "extra lessons and clubs. Good luck!")

        if not user.goals.exists():
            for g in ["Reach Level 4", "Finish English Reading Mock", "Practise every day this week"]:
                Goal.objects.create(user=user, title=g)

        # ---------- Boshqa o'quvchilar ----------
        students = {"jasmeen": user}
        for uname, fn, ln, pts, days, eng in DEMO_STUDENTS:
            u = make_user(uname, fn, ln)
            u.last_login = now - timedelta(days=days)
            u.save()
            Profile.objects.filter(user=u).update(points=pts, level=1 + pts // 500)
            Enrollment.objects.update_or_create(user=u, course=courses["english"],
                                                defaults=dict(progress=eng, milestone=2 + eng // 40))
            students[uname] = u

        # ---------- Tutor ----------
        tutor = make_user("tutor1", "Dilshod", "Karimov", role="tutor")
        tutor.email = "tutor1@pearson.uz"
        tutor.last_login = now
        tutor.save()

        if not Group.objects.filter(tutor=tutor).exists():
            ga = Group.objects.create(name="10-A", tutor=tutor, course=courses["english"])
            gb = Group.objects.create(name="10-B", tutor=tutor, course=courses["english"])
            ga.students.set([students[k] for k in ("jasmeen", "aziza", "bobur", "dilnoza")])
            gb.students.set([students[k] for k in ("sardor", "madina")])

            def assign(group, title, desc, kind, delta, pts, results):
                """results: {username: (done, hours_ago, answer, score, feedback)}"""
                a = Assignment.objects.create(tutor=tutor, group=group, title=title, description=desc, kind=kind,
                                              course=courses["english"], minutes=30, points=pts,
                                              due_date=today + timedelta(days=delta))
                for st in group.students.all():
                    done, hours, answer, score, fb = results.get(st.username, (False, 0, "", None, ""))
                    t = Task.objects.create(
                        user=st, assignment=a, assigned_by=tutor, title=title, description=desc,
                        course=courses["english"], kind=kind, minutes=30, due_date=a.due_date, done=done,
                        answer=answer, score=score, feedback=fb, points_awarded=done,
                        submitted_at=(now - timedelta(hours=hours)) if done else None)
                    if score is not None:
                        Grade.objects.create(user=st, course=courses["english"], title=title, score=score,
                                             max_score=100, task=t, date=today)
                    Message.objects.create(recipient=st, author=tutor, sender="Dilshod Karimov",
                                           subject=f"📝 {title}", body=f"{desc}\n\n⏰ {a.due_date:%Y-%m-%d}")
                return a

            assign(ga, "Essay: My future career", "Write 150–200 words about the job you want to have and why.",
                   "writing", 3, 30, {
                       "jasmeen": (True, 20, "I want to become a software engineer because I love solving problems...", 90, "Great ideas! Watch your articles (a/the)."),
                       "bobur": (True, 5, "My dream job is doctor...", None, ""),
                       "dilnoza": (True, 30, "In the future I will be a teacher...", 84, "Good structure. Add more details."),
                   })
            assign(ga, "Reading homework – Unit 5", "Read Unit 5 and answer questions 1–10.", "homework", -2, 20, {
                "jasmeen": (True, 70, "", 85, "Well done."),
                "aziza": (True, 50, "", None, ""),
                "bobur": (True, 240, "", 70, "Review questions 7–9."),
            })
            assign(gb, "Speaking: Describe your city", "Record yourself speaking for 2 minutes about Tashkent.",
                   "speaking", 2, 25, {"madina": (True, 3, "Tashkent is the capital of Uzbekistan...", None, "")})

            TutorNote.objects.create(tutor=tutor, student=students["bobur"],
                                     text="Has not been active for a while — talk to him after class.")
            Message.objects.create(recipient=students["jasmeen"], author=tutor, sender="Dilshod Karimov",
                                   subject="Well done this week!", body="Keep going — your results are improving.")

        self.stdout.write(self.style.SUCCESS(
            "Tayyor!  O'quvchi: jasmeen / pearson123   |   Tutor: tutor1 / pearson123"))
