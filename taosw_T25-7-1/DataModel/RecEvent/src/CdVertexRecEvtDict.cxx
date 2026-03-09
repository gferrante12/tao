// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldIRecEventdIsrcdICdVertexRecEvtDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/CdVertexRecEvt.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLCdVertexRecEvt(void *p = nullptr);
   static void *newArray_TaocLcLCdVertexRecEvt(Long_t size, void *p);
   static void delete_TaocLcLCdVertexRecEvt(void *p);
   static void deleteArray_TaocLcLCdVertexRecEvt(void *p);
   static void destruct_TaocLcLCdVertexRecEvt(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::CdVertexRecEvt*)
   {
      ::Tao::CdVertexRecEvt *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::CdVertexRecEvt >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::CdVertexRecEvt", ::Tao::CdVertexRecEvt::Class_Version(), "Event/CdVertexRecEvt.h", 37,
                  typeid(::Tao::CdVertexRecEvt), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::CdVertexRecEvt::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::CdVertexRecEvt) );
      instance.SetNew(&new_TaocLcLCdVertexRecEvt);
      instance.SetNewArray(&newArray_TaocLcLCdVertexRecEvt);
      instance.SetDelete(&delete_TaocLcLCdVertexRecEvt);
      instance.SetDeleteArray(&deleteArray_TaocLcLCdVertexRecEvt);
      instance.SetDestructor(&destruct_TaocLcLCdVertexRecEvt);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::CdVertexRecEvt*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::CdVertexRecEvt*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::CdVertexRecEvt*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr CdVertexRecEvt::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *CdVertexRecEvt::Class_Name()
{
   return "Tao::CdVertexRecEvt";
}

//______________________________________________________________________________
const char *CdVertexRecEvt::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdVertexRecEvt*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int CdVertexRecEvt::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdVertexRecEvt*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *CdVertexRecEvt::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdVertexRecEvt*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *CdVertexRecEvt::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdVertexRecEvt*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void CdVertexRecEvt::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::CdVertexRecEvt.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::CdVertexRecEvt::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::CdVertexRecEvt::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLCdVertexRecEvt(void *p) {
      return  p ? new(p) ::Tao::CdVertexRecEvt : new ::Tao::CdVertexRecEvt;
   }
   static void *newArray_TaocLcLCdVertexRecEvt(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::CdVertexRecEvt[nElements] : new ::Tao::CdVertexRecEvt[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLCdVertexRecEvt(void *p) {
      delete (static_cast<::Tao::CdVertexRecEvt*>(p));
   }
   static void deleteArray_TaocLcLCdVertexRecEvt(void *p) {
      delete [] (static_cast<::Tao::CdVertexRecEvt*>(p));
   }
   static void destruct_TaocLcLCdVertexRecEvt(void *p) {
      typedef ::Tao::CdVertexRecEvt current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::CdVertexRecEvt

namespace ROOT {
   static TClass *vectorlEdoublegR_Dictionary();
   static void vectorlEdoublegR_TClassManip(TClass*);
   static void *new_vectorlEdoublegR(void *p = nullptr);
   static void *newArray_vectorlEdoublegR(Long_t size, void *p);
   static void delete_vectorlEdoublegR(void *p);
   static void deleteArray_vectorlEdoublegR(void *p);
   static void destruct_vectorlEdoublegR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<double>*)
   {
      vector<double> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<double>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<double>", -2, "vector", 389,
                  typeid(vector<double>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlEdoublegR_Dictionary, isa_proxy, 0,
                  sizeof(vector<double>) );
      instance.SetNew(&new_vectorlEdoublegR);
      instance.SetNewArray(&newArray_vectorlEdoublegR);
      instance.SetDelete(&delete_vectorlEdoublegR);
      instance.SetDeleteArray(&deleteArray_vectorlEdoublegR);
      instance.SetDestructor(&destruct_vectorlEdoublegR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<double> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<double>","std::vector<double, std::allocator<double> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<double>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlEdoublegR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<double>*>(nullptr))->GetClass();
      vectorlEdoublegR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlEdoublegR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlEdoublegR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<double> : new vector<double>;
   }
   static void *newArray_vectorlEdoublegR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<double>[nElements] : new vector<double>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlEdoublegR(void *p) {
      delete (static_cast<vector<double>*>(p));
   }
   static void deleteArray_vectorlEdoublegR(void *p) {
      delete [] (static_cast<vector<double>*>(p));
   }
   static void destruct_vectorlEdoublegR(void *p) {
      typedef vector<double> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<double>

namespace {
  void TriggerDictionaryInitialization_CdVertexRecEvtDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/CdVertexRecEvt.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/RecEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/RecEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "CdVertexRecEvtDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/CdVertexRecEvt.h")))  CdVertexRecEvt;}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "CdVertexRecEvtDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/CdVertexRecEvt.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::CdVertexRecEvt", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("CdVertexRecEvtDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_CdVertexRecEvtDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_CdVertexRecEvtDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_CdVertexRecEvtDict() {
  TriggerDictionaryInitialization_CdVertexRecEvtDict_Impl();
}
