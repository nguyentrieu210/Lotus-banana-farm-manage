import unittest

from lotus_farm.mobile_roles import mobile_features, visible_line


class MobileRoleTests(unittest.TestCase):
    def test_role_union_not_exclusive_profile(self):
        features = mobile_features({"Lotus Team Leader", "Lotus Field Technician"})
        self.assertIn("tasks", features)
        self.assertIn("observation", features)
        self.assertNotIn("assign", features)

    def test_unknown_role_cannot_see_work(self):
        self.assertEqual(mobile_features({"Guest", "Employee"}), [])
        self.assertFalse(visible_line({"work_team": "A", "responsible": "a@example.com"},
                                      user="a@example.com", roles={"Employee"}, team_names=["A"]))

    def test_team_leader_sees_own_team_only(self):
        user = "leader@example.com"
        roles = {"Lotus Team Leader"}
        self.assertTrue(visible_line({"work_team": "T1"}, user=user, roles=roles, team_names=["T1"]))
        self.assertFalse(visible_line({"work_team": "T2"}, user=user, roles=roles, team_names=["T1"]))

    def test_technician_sees_only_personal_assignment(self):
        roles = {"Lotus Field Technician"}
        self.assertTrue(visible_line({"responsible": "tech@example.com", "work_team": "T2"},
                                     user="tech@example.com", roles=roles))
        self.assertFalse(visible_line({"responsible": "other@example.com", "work_team": "T2"},
                                      user="tech@example.com", roles=roles))

    def test_multiple_roles_union_and_director_scope(self):
        row = {"work_team": "T2", "responsible": "someone"}
        self.assertTrue(visible_line(row, user="u", roles={"Lotus Farm Director"}))
        self.assertTrue(visible_line(row, user="u", roles={"Lotus Team Leader", "Lotus Farm Manager"}))
        self.assertTrue(visible_line(row, user="u", roles=set(), administrator=True))


if __name__ == "__main__":
    unittest.main()
