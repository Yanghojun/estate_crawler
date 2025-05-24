from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import datetime
import httpx

mcp = FastMCP("crawler")


async def _start(data_url,
            data_headers):
    try:

        # async with aiohttp.ClientSession() as session:
        #     today_yyyymm = datetime.datetime.today().strftime("%Y%m") 
        #     data_params = {
        #         "reqData": {
        #             "inqirePd": today_yyyymm
        #             }
        #     }
        
        #     async with session.post(data_url, json=data_params, headers=data_headers) as response:
        #         response.raise_for_status()
        #         response_data = await response.json()
        #         return response_data['schdulList']

        today_yyyymm = datetime.datetime.today().strftime("%Y%m")
        data_params = {
            "reqData": {
                "inqirePd": today_yyyymm
            }
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(data_url, json=data_params, headers=data_headers)
            response.raise_for_status()
            response_data = response.json()
            return response_data['schdulList']

    except Exception as e:
        return f"예상치 못한 오류 발생: {e}"

@mcp.tool(
  name="get_result",
  description="대한민국의 아파트의 청약, 민간사전청약아파트, 민간임대오피스텔 등의 정보를 수집할 수 있는 tool입니다."
)
async def get_result(
    # user_query:str,
    house_type:str,
    jiyeok:str):
    """
    대한민국의 아파트의 청약, 민간사전청약아파트, 민간임대오피스텔 등의 정보를 수집할 수 있는 tool입니다.

    Args:
        house_type: 아파트, 민간사전청약아파트, 민간임대오피스텔, 공공지원민간임대 중 선택합니다. 특정 유형을 선택할 수 없다면 '전체'를 선택하세요. (e.g. "전체", "아파트", "민간사전청약아파트", "민간임대오피스텔", "공공지원민간임대")
        jiyeok: 지역 이름을 추출합니다. 특정 지역을 추출할 수 없다면 '전체'를 선택하세요. (e.g. "전체", "서울특별시", "대구광역시", "전라남도", "부산광역시")
    """

    load_dotenv()       # tool 호출했을 때 환경변수 Load

    info_url: list = [
        "https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancDetail.do", # se : 01 or 09
        "https://www.applyhome.co.kr/ai/aia/selectAPTRemndrLttotPblancDetailView.do", # se : 04 or 06 or 11
        "https://www.applyhome.co.kr/ai/aia/selectPRMOLttotPblancDetailView.do"
    ]
    
    data_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }

    data_url: str = "https://www.applyhome.co.kr/ai/aib/selectSubscrptCalender.do"

    type_keys: dict[str, list] = {
        "아파트": ["01","02", "03", "06", "07", "11"],
        "민간사전청약아파트": ["08", "09", "10"],
        "민간임대오피스텔": ["05"],
        "공공지원민간임대": ["04"],
    }

    jiyeok_keys: dict[str, list] = {
        "서울특별시": ["서울"],
        "광주광역시": ["광주"],
        "대구광역시": ["대구"],
        "대전광역시": ["대전"],
        "부산광역시": ["부산"],
        "세종특별자치시": ["세종"],
        "울산광역시": ["울산"],
        "인천광역시": ["인천"],

        "강원특별자치도": ["강원"],
        "경기도": ["경기"],
        "경상남도": ["경남"],
        "경상북도": ["경북"],
        "전라남도": ["전남"],
        "전라북도": ["전북"],
        "제주특별자치도": ["제주"],
        "충청남도": ["충남"],
        "충청북도": ["충북"],
    }

    enum_jiyeok : str = "서울 광주 대구 대전 부산 세종 울산 인천 강원 경기 경북 \
        경남 전남 전북 제주 충남 충북"

    data_list = await _start(data_url,
                       data_headers)

    house_type_list = []
    jiyeok_list = []

    return data_list

if __name__ == "__main__":
    print("MCP Server Start")
    mcp.run("stdio")