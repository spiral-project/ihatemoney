import pytest
from unittest.mock import Mock
from ihatemoney.models import Project, Bill


@pytest.fixture
def test_filter_by_date(Project):
    # Prepare mock data
    mock_query = Mock()
    start_date = '2024-01-01'
    end_date = '2024-12-31'

    # Mock the methods being called inside filter_by_date
    Project.query.filter.return_value = Mock()  # Assuming you're using SQLAlchemy's Query object

    # Call the method to test
    result = Project.filter_by_date(mock_query, start_date, end_date)

    # Assertions
    assert result == Project.query.filter.return_value  # Check if the method returns the expected result
    Project.query.filter.assert_called_once_with(Bill.date >= start_date,
                                                 Bill.date <= end_date)  # Check if filter was called with the correct arguments


def test_get_filtered_date_bill_weights_ordered(Project):
    # Prepare mock data
    start_date = '2024-01-01'
    end_date = '2024-12-31'


    Project.get_bill_weights_ordered.return_value = Mock()
    Project.filter_by_date.return_value = Mock()

    # Call the method to test
    result = Project.get_filtered_date_bill_weights_ordered(start_date, end_date)

    # Assertions
    assert result == Project.filter_by_date.return_value  # Check if the method returns the expected result
    Project.filter_by_date.assert_called_once_with(
        Project.get_bill_weights_ordered.return_value, start_date,
        end_date)  # Check if filter_by_date was called with the correct arguments
