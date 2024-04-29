import pytest
from niamoto.api.mapper import ApiMapper


@pytest.mark.usefixtures("niamoto_home")
class TestApiMapper:
    def test_add_new_mapping(self, mocker):
        mock_mapper_service = mocker.patch("niamoto.api.mapper.MapperService")
        api_mapper = ApiMapper()
        mock_mapper_service.return_value.add_mapping.return_value = "Mapping added"

        result = api_mapper.add_new_mapping("field")

        mock_mapper_service.return_value.add_mapping.assert_called_once_with("field")
        assert result == "Mapping added"
