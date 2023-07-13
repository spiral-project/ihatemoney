import unittest

from ihatemoney import history, models
from ihatemoney.tests.common.help_functions import em_surround
from ihatemoney.tests.common.ihatemoney_testcase import IhatemoneyTestCase
from ihatemoney.versioning import LoggingMode


class HistoryTestCase(IhatemoneyTestCase):
    def setUp(self):
        super().setUp()
        self.post_project("demo")
        self.login("demo")

    def test_simple_create_logentry_no_ip(self):
        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(f"Project {em_surround('demo')} added", resp.data.decode("utf-8"))
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 1)
        self.assertNotIn("127.0.0.1", resp.data.decode("utf-8"))

    def change_privacy_to(self, logging_preference):
        # Change only logging_preferences
        new_data = {
            "name": "demo",
            "contact_email": "demo@notmyidea.org",
            "password": "demo",
            "default_currency": "XXX",
        }

        if logging_preference != LoggingMode.DISABLED:
            new_data["project_history"] = "y"
            if logging_preference == LoggingMode.RECORD_IP:
                new_data["ip_recording"] = "y"

        # Disable History
        resp = self.client.post("/demo/edit", data=new_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("alert-danger", resp.data.decode("utf-8"))

        resp = self.client.get("/demo/edit")
        self.assertEqual(resp.status_code, 200)
        if logging_preference == LoggingMode.DISABLED:
            self.assertIn('<input id="project_history"', resp.data.decode("utf-8"))
        else:
            self.assertIn(
                '<input checked id="project_history"', resp.data.decode("utf-8")
            )

        if logging_preference == LoggingMode.RECORD_IP:
            self.assertIn('<input checked id="ip_recording"', resp.data.decode("utf-8"))
        else:
            self.assertIn('<input id="ip_recording"', resp.data.decode("utf-8"))

    def assert_empty_history_logging_disabled(self):
        resp = self.client.get("/demo/history")
        self.assertIn(
            "This project has history disabled. New actions won't appear below.",
            resp.data.decode("utf-8"),
        )
        self.assertIn("Nothing to list", resp.data.decode("utf-8"))
        self.assertNotIn(
            "The table below reflects actions recorded prior to disabling project history.",
            resp.data.decode("utf-8"),
        )
        self.assertNotIn(
            "Some entries below contain IP addresses,", resp.data.decode("utf-8")
        )
        self.assertNotIn("127.0.0.1", resp.data.decode("utf-8"))
        self.assertNotIn("<td> -- </td>", resp.data.decode("utf-8"))
        self.assertNotIn(
            f"Project {em_surround('demo')} added", resp.data.decode("utf-8")
        )

    def test_project_edit(self):
        new_data = {
            "name": "demo2",
            "contact_email": "demo2@notmyidea.org",
            "password": "123456",
            "project_history": "y",
            "default_currency": "USD",  # Currency changed from default
        }

        resp = self.client.post("/demo/edit", data=new_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(f"Project {em_surround('demo')} added", resp.data.decode("utf-8"))
        self.assertIn(
            f"Project contact email changed to {em_surround('demo2@notmyidea.org')}",
            resp.data.decode("utf-8"),
        )
        self.assertIn("Project private code changed", resp.data.decode("utf-8"))
        self.assertIn(
            f"Project renamed to {em_surround('demo2')}", resp.data.decode("utf-8")
        )
        self.assertLess(
            resp.data.decode("utf-8").index("Project renamed "),
            resp.data.decode("utf-8").index("Project contact email changed to "),
        )
        self.assertLess(
            resp.data.decode("utf-8").index("Project renamed "),
            resp.data.decode("utf-8").index("Project private code changed"),
        )
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 5)
        self.assertNotIn("127.0.0.1", resp.data.decode("utf-8"))

    def test_project_privacy_edit(self):
        resp = self.client.get("/demo/edit")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            '<input checked id="project_history" name="project_history" type="checkbox" value="y">',
            resp.data.decode("utf-8"),
        )

        self.change_privacy_to(LoggingMode.DISABLED)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Disabled Project History\n", resp.data.decode("utf-8"))
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 2)
        self.assertNotIn("127.0.0.1", resp.data.decode("utf-8"))

        self.change_privacy_to(LoggingMode.RECORD_IP)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "Enabled Project History & IP Address Recording", resp.data.decode("utf-8")
        )
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 2)
        self.assertEqual(resp.data.decode("utf-8").count("127.0.0.1"), 1)

        self.change_privacy_to(LoggingMode.ENABLED)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Disabled IP Address Recording\n", resp.data.decode("utf-8"))
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 2)
        self.assertEqual(resp.data.decode("utf-8").count("127.0.0.1"), 2)

    def test_project_privacy_edit2(self):
        self.change_privacy_to(LoggingMode.RECORD_IP)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Enabled IP Address Recording\n", resp.data.decode("utf-8"))
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 1)
        self.assertEqual(resp.data.decode("utf-8").count("127.0.0.1"), 1)

        self.change_privacy_to(LoggingMode.DISABLED)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "Disabled Project History & IP Address Recording", resp.data.decode("utf-8")
        )
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 1)
        self.assertEqual(resp.data.decode("utf-8").count("127.0.0.1"), 2)

        self.change_privacy_to(LoggingMode.ENABLED)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Enabled Project History\n", resp.data.decode("utf-8"))
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 2)
        self.assertEqual(resp.data.decode("utf-8").count("127.0.0.1"), 2)

    def do_misc_database_operations(self, logging_mode):
        new_data = {
            "name": "demo2",
            "contact_email": "demo2@notmyidea.org",
            "password": "123456",
            "default_currency": "USD",
        }

        # Keep privacy settings where they were
        if logging_mode != LoggingMode.DISABLED:
            new_data["project_history"] = "y"
            if logging_mode == LoggingMode.RECORD_IP:
                new_data["ip_recording"] = "y"

        resp = self.client.post("/demo/edit", data=new_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # adds a member to this project
        resp = self.client.post(
            "/demo/members/add", data={"name": "zorglub"}, follow_redirects=True
        )
        self.assertEqual(resp.status_code, 200)

        user_id = models.Person.query.one().id

        # create a bill
        resp = self.client.post(
            "/demo/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": user_id,
                "payed_for": [user_id],
                "amount": "25",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)

        bill_id = models.Bill.query.one().id

        # edit the bill
        resp = self.client.post(
            f"/demo/edit/{bill_id}",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": user_id,
                "payed_for": [user_id],
                "amount": "10",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        # delete the bill
        resp = self.client.post(f"/demo/delete/{bill_id}", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # delete user using POST method
        resp = self.client.post(
            f"/demo/members/{user_id}/delete", follow_redirects=True
        )
        self.assertEqual(resp.status_code, 200)

    def test_disable_clear_no_new_records(self):
        # Disable logging
        self.change_privacy_to(LoggingMode.DISABLED)

        # Ensure we can't clear history with a GET or with a password-less POST
        resp = self.client.get("/demo/erase_history")
        self.assertEqual(resp.status_code, 405)
        resp = self.client.post("/demo/erase_history", follow_redirects=True)
        self.assertIn(
            "Error deleting project history",
            resp.data.decode("utf-8"),
        )

        # List history
        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "This project has history disabled. New actions won't appear below.",
            resp.data.decode("utf-8"),
        )
        self.assertIn(
            "The table below reflects actions recorded prior to disabling project history.",
            resp.data.decode("utf-8"),
        )
        self.assertNotIn("Nothing to list", resp.data.decode("utf-8"))
        self.assertNotIn(
            "Some entries below contain IP addresses,", resp.data.decode("utf-8")
        )

        # Clear Existing Entries
        resp = self.client.post(
            "/demo/erase_history",
            data={"password": "demo"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assert_empty_history_logging_disabled()

        # Do lots of database operations & check that there's still no history
        self.do_misc_database_operations(LoggingMode.DISABLED)

        self.assert_empty_history_logging_disabled()

    def test_clear_ip_records(self):
        # Enable IP Recording
        self.change_privacy_to(LoggingMode.RECORD_IP)

        # Do lots of database operations to generate IP address entries
        self.do_misc_database_operations(LoggingMode.RECORD_IP)

        # Disable IP Recording
        self.change_privacy_to(LoggingMode.ENABLED)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(
            "This project has history disabled. New actions won't appear below.",
            resp.data.decode("utf-8"),
        )
        self.assertNotIn(
            "The table below reflects actions recorded prior to disabling project history.",
            resp.data.decode("utf-8"),
        )
        self.assertNotIn("Nothing to list", resp.data.decode("utf-8"))
        self.assertIn(
            "Some entries below contain IP addresses,", resp.data.decode("utf-8")
        )
        self.assertEqual(resp.data.decode("utf-8").count("127.0.0.1"), 12)
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 1)

        # Generate more operations to confirm additional IP info isn't recorded
        self.do_misc_database_operations(LoggingMode.ENABLED)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.decode("utf-8").count("127.0.0.1"), 12)
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 7)

        # Ensure we can't clear IP data with a GET or with a password-less POST
        resp = self.client.get("/demo/strip_ip_addresses")
        self.assertEqual(resp.status_code, 405)
        resp = self.client.post("/demo/strip_ip_addresses", follow_redirects=True)
        self.assertIn(
            "Error deleting recorded IP addresses",
            resp.data.decode("utf-8"),
        )

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.decode("utf-8").count("127.0.0.1"), 12)
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 7)

        # Clear IP Data
        resp = self.client.post(
            "/demo/strip_ip_addresses",
            data={"password": "123456"},
            follow_redirects=True,
        )

        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(
            "This project has history disabled. New actions won't appear below.",
            resp.data.decode("utf-8"),
        )
        self.assertNotIn(
            "The table below reflects actions recorded prior to disabling project history.",
            resp.data.decode("utf-8"),
        )
        self.assertNotIn("Nothing to list", resp.data.decode("utf-8"))
        self.assertNotIn(
            "Some entries below contain IP addresses,", resp.data.decode("utf-8")
        )
        self.assertEqual(resp.data.decode("utf-8").count("127.0.0.1"), 0)
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 19)

    def test_logs_for_common_actions(self):
        # adds a member to this project
        resp = self.client.post(
            "/demo/members/add", data={"name": "zorglub"}, follow_redirects=True
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            f"Participant {em_surround('zorglub')} added", resp.data.decode("utf-8")
        )

        # create a bill
        resp = self.client.post(
            "/demo/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1],
                "amount": "25",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            f"Bill {em_surround('fromage à raclette')} added",
            resp.data.decode("utf-8"),
        )

        # edit the bill
        resp = self.client.post(
            "/demo/edit/1",
            data={
                "date": "2011-08-10",
                "what": "new thing",
                "payer": 1,
                "payed_for": [1],
                "amount": "10",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            f"Bill {em_surround('fromage à raclette')} added",
            resp.data.decode("utf-8"),
        )
        self.assertRegex(
            resp.data.decode("utf-8"),
            r"Bill %s:\s* Amount changed\s* from %s\s* to %s"
            % (
                em_surround("fromage à raclette", regex_escape=True),
                em_surround("25.0", regex_escape=True),
                em_surround("10.0", regex_escape=True),
            ),
        )
        self.assertIn(
            "Bill %s renamed to %s"
            % (em_surround("fromage à raclette"), em_surround("new thing")),
            resp.data.decode("utf-8"),
        )
        self.assertLess(
            resp.data.decode("utf-8").index(
                f"Bill {em_surround('fromage à raclette')} renamed to"
            ),
            resp.data.decode("utf-8").index("Amount changed"),
        )

        # delete the bill
        resp = self.client.post("/demo/delete/1", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            f"Bill {em_surround('new thing')} removed", resp.data.decode("utf-8")
        )

        # edit user
        resp = self.client.post(
            "/demo/members/1/edit",
            data={"weight": 2, "name": "new name"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertRegex(
            resp.data.decode("utf-8"),
            r"Participant %s:\s* weight changed\s* from %s\s* to %s"
            % (
                em_surround("zorglub", regex_escape=True),
                em_surround("1.0", regex_escape=True),
                em_surround("2.0", regex_escape=True),
            ),
        )
        self.assertIn(
            "Participant %s renamed to %s"
            % (em_surround("zorglub"), em_surround("new name")),
            resp.data.decode("utf-8"),
        )
        self.assertLess(
            resp.data.decode("utf-8").index(
                f"Participant {em_surround('zorglub')} renamed"
            ),
            resp.data.decode("utf-8").index("weight changed"),
        )

        # delete user using POST method
        resp = self.client.post("/demo/members/1/delete", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            f"Participant {em_surround('new name')} removed", resp.data.decode("utf-8")
        )

    def test_double_bill_double_person_edit_second(self):
        # add two members
        self.client.post("/demo/members/add", data={"name": "User 1"})
        self.client.post("/demo/members/add", data={"name": "User 2"})

        # add two bills
        self.client.post(
            "/demo/add",
            data={
                "date": "2020-04-13",
                "what": "Bill 1",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "25",
            },
        )
        self.client.post(
            "/demo/add",
            data={
                "date": "2020-04-13",
                "what": "Bill 2",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "20",
            },
        )

        # Should be 5 history entries at this point
        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 5)
        self.assertNotIn("127.0.0.1", resp.data.decode("utf-8"))

        # Edit ONLY the amount on the first bill
        self.client.post(
            "/demo/edit/1",
            data={
                "date": "2020-04-13",
                "what": "Bill 1",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "88",
            },
        )

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertRegex(
            resp.data.decode("utf-8"),
            r"Bill {}:\s* Amount changed\s* from {}\s* to {}".format(
                em_surround("Bill 1", regex_escape=True),
                em_surround("25.0", regex_escape=True),
                em_surround("88.0", regex_escape=True),
            ),
        )

        self.assertNotRegex(
            resp.data.decode("utf-8"),
            r"Removed\s* {}\s* and\s* {}\s* from\s* owers list".format(
                em_surround("User 1", regex_escape=True),
                em_surround("User 2", regex_escape=True),
            ),
            resp.data.decode("utf-8"),
        )

        # Should be 6 history entries at this point
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 6)
        self.assertNotIn("127.0.0.1", resp.data.decode("utf-8"))

    def test_bill_add_remove_add(self):
        # add two members
        self.client.post("/demo/members/add", data={"name": "User 1"})
        self.client.post("/demo/members/add", data={"name": "User 2"})

        # add 1 bill
        self.client.post(
            "/demo/add",
            data={
                "date": "2020-04-13",
                "what": "Bill 1",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "25",
            },
        )

        # delete the bill
        self.client.post("/demo/delete/1", follow_redirects=True)

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 5)
        self.assertNotIn("127.0.0.1", resp.data.decode("utf-8"))
        self.assertIn(f"Bill {em_surround('Bill 1')} added", resp.data.decode("utf-8"))
        self.assertIn(
            f"Bill {em_surround('Bill 1')} removed", resp.data.decode("utf-8")
        )

        # Add a new bill
        self.client.post(
            "/demo/add",
            data={
                "date": "2020-04-13",
                "what": "Bill 2",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "20",
            },
        )

        resp = self.client.get("/demo/history")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.decode("utf-8").count("<td> -- </td>"), 6)
        self.assertNotIn("127.0.0.1", resp.data.decode("utf-8"))
        self.assertIn(f"Bill {em_surround('Bill 1')} added", resp.data.decode("utf-8"))
        self.assertEqual(
            resp.data.decode("utf-8").count(f"Bill {em_surround('Bill 1')} added"), 1
        )
        self.assertIn(f"Bill {em_surround('Bill 2')} added", resp.data.decode("utf-8"))
        self.assertIn(
            f"Bill {em_surround('Bill 1')} removed", resp.data.decode("utf-8")
        )

    def test_double_bill_double_person_edit_second_no_web(self):
        u1 = models.Person(project_id="demo", name="User 1")
        u2 = models.Person(project_id="demo", name="User 1")

        models.db.session.add(u1)
        models.db.session.add(u2)
        models.db.session.commit()

        b1 = models.Bill(what="Bill 1", payer_id=u1.id, owers=[u2], amount=10)
        b2 = models.Bill(what="Bill 2", payer_id=u2.id, owers=[u2], amount=11)

        # This db commit exposes the "spurious owers edit" bug
        models.db.session.add(b1)
        models.db.session.commit()

        models.db.session.add(b2)
        models.db.session.commit()

        history_list = history.get_history(self.get_project("demo"))
        self.assertEqual(len(history_list), 5)

        # Change just the amount
        b1.amount = 5
        models.db.session.commit()

        history_list = history.get_history(self.get_project("demo"))
        for entry in history_list:
            if "prop_changed" in entry:
                self.assertNotIn("owers", entry["prop_changed"])
        self.assertEqual(len(history_list), 6)

    def test_delete_history_with_project(self):
        self.post_project("raclette", password="party")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})

        # add bill
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1],
                "amount": "10",
                "original_currency": "EUR",
            },
        )

        # Delete project
        self.client.post(
            "/raclette/delete",
            data={"password": "party"},
        )

        # Recreate it
        self.post_project("raclette", password="party")

        # History should be equal to project creation
        history_list = history.get_history(self.get_project("raclette"))
        self.assertEqual(len(history_list), 1)


if __name__ == "__main__":
    unittest.main()
